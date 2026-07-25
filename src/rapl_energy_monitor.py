"""
RAPL real-energy monitor (Rule 21.1 — close the joules gap).
=============================================================
physical_cost_model.py currently estimates joules from `joules_per_flop ~ 10 pJ`
(an order-of-magnitude figure). Rule 21.1 requires MEASURED hardware energy. This
module reads REAL joules from Intel RAPL (Running Average Power Limit) so the
substrate's energy budget maps onto actual dissipated work, not an estimate.

Three RAPL access paths are tried, in order of preference:
  1. powercap sysfs   /sys/class/powercap/intel-rapl:*/energy_uj   (root or rapl group)
  2. perf             `perf stat -e power/energy-pkg/ -- <cmd>`    (perf + kernel PMU)
  3. MSR              /dev/cpu/N/msr  MSR_PKG_ENERGY_STATUS 0x611  (msr module; validated
                      against MSR_RAPL_POWER_UNIT 0x606 so a hypervisor that stubs the
                      MSRs to zero is detected and rejected, not trusted)

If none is available the module raises RaplUnavailable with a precise, actionable
message (what is missing and the exact command to run on bare metal). It NEVER
silently falls back to the joules_per_flop estimate — that would re-introduce the
game-mechanic Rule 21 forbids.

Usage on bare-metal Intel:
    from rapl_energy_monitor import measure_joules, rapl_status
    print(rapl_status())                       # which path is live
    joules = measure_joules(lambda: run_my_workload())   # real dissipated energy
"""
import os, glob, struct, subprocess, shutil, time

MSR_RAPL_POWER_UNIT   = 0x606
MSR_PKG_ENERGY_STATUS = 0x611


class RaplUnavailable(RuntimeError):
    """Raised when no real RAPL energy source is accessible on this host."""


# --------------------------------------------------------------------------
# Path 1 — powercap sysfs (preferred)
# --------------------------------------------------------------------------
def _powercap_domains():
    """Return [(name, energy_uj_path)] for every RAPL domain that exposes energy_uj."""
    out = []
    for d in sorted(glob.glob("/sys/class/powercap/intel-rapl:*")):
        if d.count(":") != 1:                      # skip sub-domains like intel-rapl:0:0
            continue
        ej = os.path.join(d, "energy_uj")
        name = "pkg"
        nf = os.path.join(d, "name")
        if os.path.exists(nf):
            try: name = open(nf).read().strip()
            except OSError: pass
        if os.path.exists(ej):
            out.append((name, ej))
    return out


def _read_powercap_uj(domains):
    tot = 0
    for _, path in domains:
        with open(path) as f:
            tot += int(f.read().strip())
    return tot                                    # microjoules (sum across domains)


# --------------------------------------------------------------------------
# Path 3 — MSR (validated; rejects hypervisor zero-stubbing)
# --------------------------------------------------------------------------
def _msr_read(cpu, addr):
    fd = os.open(f"/dev/cpu/{cpu}/msr", os.O_RDONLY)
    try:
        os.lseek(fd, addr, os.SEEK_SET)
        return struct.unpack("<Q", os.read(fd, 8))[0]
    finally:
        os.close(fd)


def _msr_rapl_ok(cpu=0):
    """True only if the power-unit MSR is non-zero (a real RAPL device, not a stub)."""
    try:
        unit = _msr_read(cpu, MSR_RAPL_POWER_UNIT)
        return (unit & 0x1fff) != 0               # power-unit field bits 3:0 + energy bits 12:8
    except OSError:
        return False


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def rapl_status():
    """Return a dict describing which RAPL path (if any) is live on this host."""
    st = {"powercap": False, "perf": False, "msr": False, "available": False, "detail": ""}
    doms = _powercap_domains()
    if doms:
        try:
            _read_powercap_uj(doms)
            st.update(powercap=True, available=True,
                      detail=f"powercap sysfs domains: {[n for n,_ in doms]}")
            return st
        except OSError as e:
            st["detail"] = f"powercap present but unreadable ({e}); need root/rapl group"
    if shutil.which("perf"):
        st["perf"] = True
        st["available"] = True
        st["detail"] = st.get("detail", "") + " | perf present (power/energy-pkg/)"
        return st
    if os.path.exists("/dev/cpu/0/msr"):
        st["msr"] = True
        if _msr_rapl_ok():
            st["available"] = True
            st["detail"] = "MSR RAPL readable (power-unit non-zero)"
            return st
        st["detail"] = (st.get("detail", "") +
                        " | /dev/cpu/0/msr exists but RAPL MSRs read 0 "
                        "(hypervisor stub — not trustworthy)")
    if not st["detail"]:
        st["detail"] = "no powercap sysfs, no perf, no MSR device"
    return st


def measure_joules(workload, cpu=0):
    """Run `workload()` and return the REAL energy it dissipated, in joules (RAPL).

    Raises RaplUnavailable if no trustworthy RAPL source exists — never estimates.
    """
    st = rapl_status()
    # Path 1: powercap
    doms = _powercap_domains()
    if st["powercap"] and doms:
        e0 = _read_powercap_uj(doms)
        workload()
        e1 = _read_powercap_uj(doms)
        return (e1 - e0) * 1e-6                   # uJ -> J
    # Path 2: perf (run workload in-process is not measurable by perf; use a subprocess hook)
    if st["perf"] and not doms:
        raise RaplUnavailable(
            "perf is present but in-process measurement needs the perf PMU; run "
            "`perf stat -e power/energy-pkg/ python3 <script>` around the workload.")
    # Path 3: MSR
    if st["msr"] and _msr_rapl_ok(cpu):
        unit = _msr_read(cpu, MSR_RAPL_POWER_UNIT)
        energy_unit_bits = (unit >> 8) & 0x1f
        joules_per_lsb = 1.0 / (2 ** energy_unit_bits)
        e0 = _msr_read(cpu, MSR_PKG_ENERGY_STATUS) & 0xffffffff
        workload()
        e1 = _msr_read(cpu, MSR_PKG_ENERGY_STATUS) & 0xffffffff
        delta = (e1 - e0) & 0xffffffff            # 32-bit counter wrap
        return delta * joules_per_lsb
    raise RaplUnavailable(
        "RAPL unavailable on this host: " + st["detail"] +
        ". To measure real joules, run on bare-metal Intel with one of: "
        "(a) `sudo modprobe msr` + readable /sys/class/powercap/intel-rapl:0/energy_uj, "
        "(b) `sudo apt install linux-tools-common && perf stat -e power/energy-pkg/ ...`, or "
        "(c) add the user to the `rapl` group. A VM/container that stubs the RAPL MSRs to 0 "
        "cannot provide real energy — Rule 21.1 forbids substituting an estimate.")


if __name__ == "__main__":
    st = rapl_status()
    print("RAPL status:", st)
    if st["available"]:
        # sanity: measure a 1s busy spin
        j = measure_joules(lambda: time.sleep(1.0))
        print(f"~1s idle dissipated {j:.3f} J (real RAPL measurement)")
    else:
        print("BLOCKED:", st["detail"])
