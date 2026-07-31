"""Live web curriculum streamer (hardened 2026-07-31 audit).

BEFORE: `get_latest_live_text()` called `urllib.request.urlopen(..., timeout=4)` DIRECTLY —
from inside the hot `sim_loop` every 20 s and from `_lay_library()`. A slow/absent network
therefore froze the whole evolutionary loop (and the dashboard) for up to 4 s per refresh, and
every failure vanished into a bare `except Exception: pass` — violating the project's own
telemetry-honesty rules (deep review P1-9/P1-10).

NOW:
  * fetching happens ONLY on a background daemon thread (`_refresher`);
  * `get_latest_live_text()` NEVER blocks — it serves the in-memory cache (or the built-in
    topic fallback when the cache is still empty/offline);
  * failures are counted and visible via `status()` (healthy/degraded/offline) instead of being
    swallowed, and the first failure in each outage is printed once (loud, not silent);
  * the stream can be disabled explicitly with GENESIS_LIVE_WEB=0 (benchmark reproducibility,
    Rule: live demo vs reproducible benchmark separation);
  * an on-disk cache (`Brain/live_web_cache.json`, best-effort) lets an offline cold start
    still serve previously fetched text instead of the fixed fallback.
"""
import json
import os
import random
import re
import threading
import time
import urllib.request

_FETCH_INTERVAL = 20.0          # background refresh cadence (matches the old sim_loop cadence)
_CACHE_MAX = 24
_DISK_CACHE = os.path.join("Brain", "live_web_cache.json")

_state = {
    "cache": [],                # list[str]
    "last_fetch": 0.0,
    "last_success": 0.0,
    "errors": 0,
    "last_error": None,
    "offline_announced": False,
    "started": False,
}
_lock = threading.Lock()

LIVE_WEB_ENABLED = os.environ.get("GENESIS_LIVE_WEB", "1") == "1"

_TOPICS = [
    "Artificial General Intelligence and neuromorphic SNN architectures represent the frontier of continuous learning.",
    "Quantum computing and bio-inspired neural networks process parallel information at extreme efficiency.",
    "Astrophysicists observe distant galaxies using deep spatial spectrum analysis and gravitational lensing.",
    "Molecular biology advances synthetic genetic circuits for cellular computation and autonomous adaptation.",
]


def _fetch_wikipedia_random():
    """Fetch a random Wikipedia summary article text in English (blocking — thread only)."""
    url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GENESIS_Neuromorphic_AGI_Engine/3.0 (contact: research@genesis.lab)"}
    )
    with urllib.request.urlopen(req, timeout=4) as response:
        if response.status == 200:
            data = json.loads(response.read().decode("utf-8"))
            title = data.get("title", "")
            extract = data.get("extract", "")
            if extract:
                return f"=== WIKIPEDIA: {title} === {extract}"
    return None


def _save_disk_cache(items):
    try:
        os.makedirs(os.path.dirname(_DISK_CACHE), exist_ok=True)
        with open(_DISK_CACHE, "w", encoding="utf-8") as f:
            json.dump(items[-_CACHE_MAX:], f)
    except OSError:
        pass  # cache persistence is best-effort; absence is not an error condition


def _load_disk_cache():
    try:
        with open(_DISK_CACHE, "r", encoding="utf-8") as f:
            items = json.load(f)
        if isinstance(items, list):
            return [str(x) for x in items if isinstance(x, str) and x][: _CACHE_MAX]
    except (OSError, ValueError):
        pass
    return []


def _refresher():
    while True:
        try:
            text = _fetch_wikipedia_random()
            with _lock:
                _state["last_fetch"] = time.time()
                if text:
                    _state["cache"].append(text)
                    if len(_state["cache"]) > _CACHE_MAX:
                        _state["cache"].pop(0)
                    _state["last_success"] = time.time()
                    _state["offline_announced"] = False
                    _save_disk_cache(_state["cache"])
        except Exception as e:  # network class of errors is EXPECTED; record, don't swallow
            with _lock:
                _state["errors"] += 1
                _state["last_error"] = f"{type(e).__name__}: {e}"
                if not _state["offline_announced"]:
                    _state["offline_announced"] = True
                    print(f"[LIVE WEB] fetch failed ({_state['last_error']}); "
                          f"serving cache/fallback until the network recovers.", flush=True)
        time.sleep(_FETCH_INTERVAL)


def _ensure_started():
    if not LIVE_WEB_ENABLED:
        return
    with _lock:
        if _state["started"]:
            return
        _state["started"] = True
        disk = _load_disk_cache()
        if disk:
            _state["cache"].extend(disk)
    t = threading.Thread(target=_refresher, name="genesis-live-web", daemon=True)
    t.start()


def fetch_tech_news():
    """Fallback text for offline operation (deterministic pool, no network)."""
    return random.choice(_TOPICS)


def get_latest_live_text():
    """Return a clean printable text string — ALWAYS non-blocking.

    Serves the freshest cached Wikipedia/news item; falls back to the disk cache and finally
    to the built-in topic pool when the network is down. Never raises.
    """
    if not LIVE_WEB_ENABLED:
        return fetch_tech_news()
    _ensure_started()
    with _lock:
        cache = list(_state["cache"])
    if cache:
        return random.choice(cache)
    return fetch_tech_news()


def status():
    """Telemetry-honest stream health snapshot (for dashboards/manifests)."""
    with _lock:
        ok = _state["last_success"] > 0 and (time.time() - _state["last_success"]) < 3 * _FETCH_INTERVAL
        return {
            "enabled": LIVE_WEB_ENABLED,
            "healthy": bool(ok),
            "cache_size": len(_state["cache"]),
            "errors": _state["errors"],
            "last_error": _state["last_error"],
            "stale_seconds": (None if not _state["last_success"]
                              else round(time.time() - _state["last_success"], 1)),
        }


if __name__ == "__main__":
    print("Testing Live Web Streamer (non-blocking)...")
    t0 = time.time()
    text = get_latest_live_text()
    print(f"returned in {(time.time() - t0) * 1000:.2f} ms:", text[:110], "...")
    print("status:", status())
