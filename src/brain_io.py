"""Self-describing, forward-compatible Brain checkpoint (2026-07-13).

WHY THIS EXISTS
---------------
The old checkpoint was `np.savez(Brain.npz, genome=ark_dna)` — a bare byte array with NO
record of the architecture that produced it. A GENESIS genome is a *marker-based* string
(GENE_MARKER / NEURON_MARKER / RECEPTOR_MARKER) whose connections decode as
`actual_dst = dst % (N_IO + hidden_count)`. So the SAME bytes decode into a DIFFERENT brain
the moment `N_INPUT`, `N_OUTPUT` (hence `N_IO`), or a marker value changes. With no provenance
stored, every code change silently invalidated Brain.npz and the only recovery was to delete it
by hand and let a fresh one be written. This module removes that manual step.

DESIGN
------
Brain.npz is now:

  * **Self-describing** — it carries an ENGINE FINGERPRINT: the exact set of decode-relevant
    constants (imported live from `neuromorphic_engine`, so it is a *derived* quantity, never a
    tuned game constant). Any reader can check "were these bytes authored under my layout?".

  * **Forward-compatible / flexible to any change** — on save, if the on-disk fingerprint no
    longer matches the running code, the stale file is ARCHIVED (renamed `*.legacy-<fp>.npz`)
    and a fresh checkpoint is written under the new fingerprint. No crash, no manual delete.

  * **Always evolving and improving** — the file is an APPEND-ONLY, MONOTONIC hall-of-fame: each
    save MERGES the current champions with those already on disk, dedups by genome, keeps the
    single highest survival-age per genome, and retains the top-K. A champion never regresses out
    of the record unless a strictly older-surviving one displaces it. Paired with opt-in resume
    (`GENESIS_RESUME=1`, see genesis_lab), a run seeds its founders from this accumulated best-ever
    bank, so capability carries forward and compounds across sessions instead of cold-restarting.

No game constants are introduced: the fingerprint is read from the engine, `keep_k` is the
caller's existing derived pool size (`FOSSIL_POOL_MAX`), and `SCHEMA_VERSION` is file-format
metadata (versioning), not an economy/reward/seed number.

ON-DISK KEYS (all plain arrays — no pickle / allow_pickle):
  schema           : int   file-format schema version
  fp_names         : <U..  names of the fingerprint constants
  fp_values        : int64 their values (parallel to fp_names)
  genomes_blob     : uint8 all genomes concatenated
  genomes_offsets  : int64 length K+1; genome i = blob[offsets[i]:offsets[i+1]]
  ages             : int64 length K; survival-age (fitness) per genome, sorted descending
  saved_at_tick    : int64 LIF-time provenance of this save
  count            : int64 K
"""

import os
import hashlib
import tempfile
import numpy as np

# The fingerprint is EVERYTHING that determines how a genome's bytes decode into a wired brain.
# Imported live from the engine = single source of truth, recomputed every run, never hand-set.
from neuromorphic_engine import (
    N_INPUT, N_OUTPUT, N_IO,
    GENE_MARKER, NEURON_MARKER, RECEPTOR_MARKER,
    MAX_RECEPTORS_PER_ORG, RAM_SIZE,
)

SCHEMA_VERSION = 1


def current_fingerprint():
    """The decode-relevant engine constants, as an ordered dict {name: int}.

    Any change to one of these remaps how saved genome bytes decode, so a genome authored under
    one fingerprint is only faithfully interpretable under an identical one."""
    return {
        "N_INPUT": int(N_INPUT),
        "N_OUTPUT": int(N_OUTPUT),
        "N_IO": int(N_IO),
        "GENE_MARKER": int(GENE_MARKER),
        "NEURON_MARKER": int(NEURON_MARKER),
        "RECEPTOR_MARKER": int(RECEPTOR_MARKER),
        "MAX_RECEPTORS_PER_ORG": int(MAX_RECEPTORS_PER_ORG),
        "RAM_SIZE": int(RAM_SIZE),
    }


def fingerprint_hash(fp):
    """Stable 8-hex-char digest of a fingerprint dict (order-independent)."""
    canon = ";".join(f"{k}={fp[k]}" for k in sorted(fp))
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:8]


def _fp_from_loaded(data):
    """Reconstruct the fingerprint dict from a loaded npz, or None if it isn't our schema."""
    if "schema" not in data.files or "fp_names" not in data.files or "fp_values" not in data.files:
        return None
    names = [str(n) for n in data["fp_names"].tolist()]
    values = [int(v) for v in data["fp_values"].tolist()]
    return dict(zip(names, values))


def _entries_from_loaded(data):
    """Return [(age:int, genome:uint8 ndarray), ...] from a loaded npz in our schema."""
    if "genomes_blob" not in data.files or "genomes_offsets" not in data.files:
        return []
    blob = np.asarray(data["genomes_blob"], dtype=np.uint8)
    offsets = np.asarray(data["genomes_offsets"], dtype=np.int64)
    ages = np.asarray(data["ages"], dtype=np.int64) if "ages" in data.files else None
    out = []
    for i in range(len(offsets) - 1):
        g = blob[offsets[i]:offsets[i + 1]].copy()
        age = int(ages[i]) if ages is not None and i < len(ages) else 0
        out.append((age, g))
    return out


def load_brain(path):
    """Load a checkpoint WITHOUT ever raising on incompatibility.

    Returns a dict:
      ok             : bool  — True only if the file exists, is our schema, AND its fingerprint
                               matches the running engine (so its genomes decode faithfully).
      reason         : str   — 'ok' | 'missing' | 'unreadable' | 'legacy-format' | 'fingerprint-mismatch'
      match          : bool  — fingerprint equals the current engine's
      stored_fp      : dict|None
      entries        : [(age, genome ndarray)]  (only when ok)
      saved_at_tick  : int
    """
    result = {"ok": False, "reason": "missing", "match": False,
              "stored_fp": None, "entries": [], "saved_at_tick": 0}
    if not os.path.exists(path):
        return result
    try:
        data = np.load(path, allow_pickle=False)
    except Exception as e:
        result["reason"] = "unreadable"
        result["error"] = str(e)
        return result

    stored_fp = _fp_from_loaded(data)
    result["stored_fp"] = stored_fp
    if stored_fp is None:
        result["reason"] = "legacy-format"        # old bare `genome=`/`genomes=`/`memory=` file
        return result

    cur = current_fingerprint()
    if stored_fp == cur:
        result["ok"] = True
        result["reason"] = "ok"
        result["match"] = True
        result["entries"] = _entries_from_loaded(data)
        if "saved_at_tick" in data.files:
            result["saved_at_tick"] = int(data["saved_at_tick"])
    else:
        result["reason"] = "fingerprint-mismatch"
    return result


def _archive_stale(path, stored_fp):
    """Rename an incompatible checkpoint aside so a fresh one can take its place.

    Names the archive by the OLD fingerprint hash so successive incompatible files never collide.
    Returns the archive path (or None if nothing was moved)."""
    if not os.path.exists(path):
        return None
    tag = fingerprint_hash(stored_fp) if stored_fp else "unknown"
    base, ext = os.path.splitext(path)          # ('.../Brain', '.npz')
    archive = f"{base}.legacy-{tag}{ext}"
    n = 1
    while os.path.exists(archive):
        archive = f"{base}.legacy-{tag}.{n}{ext}"
        n += 1
    os.replace(path, archive)
    return archive


def _write_atomic(path, arrays):
    """np.savez to a temp file in the same dir, then atomically replace `path`."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".npz")
    os.close(fd)
    try:
        # np.savez APPENDS .npz if the name lacks it; tmp already ends in .npz, so the written
        # file is exactly `tmp`.
        np.savez(tmp, **arrays)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def save_brain(path, hall_of_fame, saved_at_tick, keep_k):
    """Merge `hall_of_fame` into the on-disk checkpoint and write it back (monotonic).

    hall_of_fame : iterable of (age:int, genome:1-D uint8 array-like) — this run's champions.
    saved_at_tick: LIF-time of this save (provenance only).
    keep_k       : max genomes to retain (caller passes its derived pool size, e.g. FOSSIL_POOL_MAX).

    Behaviour:
      * If the existing file's fingerprint MATCHES, its champions are merged in (accumulation).
      * If it MISMATCHES / is legacy / is unreadable, it is ARCHIVED and a fresh record is started
        under the current fingerprint — so a code change never needs a manual delete.
      * Dedup by genome bytes, keep the max age per genome, keep the top-K by age.

    Returns (num_kept:int, archived_path:str|None).
    """
    cur = current_fingerprint()
    archived = None

    # Start the merge set from whatever is compatibly on disk.
    merged = {}   # genome bytes -> max age
    loaded = load_brain(path)
    if loaded["ok"]:
        for age, g in loaded["entries"]:
            b = np.asarray(g, dtype=np.uint8).tobytes()
            if b and age > merged.get(b, -1):
                merged[b] = age
    elif loaded["reason"] in ("fingerprint-mismatch", "legacy-format", "unreadable"):
        archived = _archive_stale(path, loaded.get("stored_fp"))

    # Fold in this run's champions.
    for age, g in hall_of_fame:
        if g is None:
            continue
        b = np.asarray(g, dtype=np.uint8).tobytes()
        if b and int(age) > merged.get(b, -1):
            merged[b] = int(age)

    if not merged:
        return 0, archived

    # Sort by fitness (survival age) descending, keep top-K.
    items = sorted(merged.items(), key=lambda kv: kv[1], reverse=True)[:max(1, int(keep_k))]

    genomes = [np.frombuffer(b, dtype=np.uint8) for b, _ in items]
    ages = np.array([a for _, a in items], dtype=np.int64)
    offsets = np.zeros(len(genomes) + 1, dtype=np.int64)
    for i, g in enumerate(genomes):
        offsets[i + 1] = offsets[i] + g.size
    blob = np.concatenate(genomes).astype(np.uint8) if genomes else np.zeros(0, dtype=np.uint8)

    fp_names = np.array(list(cur.keys()))
    fp_values = np.array([cur[k] for k in cur], dtype=np.int64)

    _write_atomic(path, {
        "schema": np.int64(SCHEMA_VERSION),
        "fp_names": fp_names,
        "fp_values": fp_values,
        "genomes_blob": blob,
        "genomes_offsets": offsets,
        "ages": ages,
        "saved_at_tick": np.int64(int(saved_at_tick)),
        "count": np.int64(len(genomes)),
    })
    return len(genomes), archived
