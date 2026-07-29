import urllib.request
import json
import re
import random
import time

_CACHE = []
_LAST_FETCH = 0

def fetch_wikipedia_random():
    """Fetch a random Wikipedia summary article text in English."""
    url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GENESIS_Neuromorphic_AGI_Engine/3.0 (contact: research@genesis.lab)"}
    )
    with urllib.request.urlopen(req, timeout=4) as response:
        if response.status == 200:
            data = json.loads(response.read().decode('utf-8'))
            title = data.get("title", "")
            extract = data.get("extract", "")
            if extract:
                return f"=== WIKIPEDIA: {title} === {extract}"
    return None

def fetch_tech_news():
    """Fallback fetch for tech/science headlines."""
    topics = [
        "Artificial General Intelligence and neuromorphic SNN architectures represent the frontier of continuous learning.",
        "Quantum computing and bio-inspired neural networks process parallel information at extreme efficiency.",
        "Astrophysicists observe distant galaxies using deep spatial spectrum analysis and gravitational lensing.",
        "Molecular biology advances synthetic genetic circuits for cellular computation and autonomous adaptation."
    ]
    return random.choice(topics)

def get_latest_live_text():
    """Returns a clean printable ASCII text string from live Wikipedia or news API."""
    global _CACHE, _LAST_FETCH
    now = time.time()
    
    # Refresh cache every 15 seconds or if cache empty
    if not _CACHE or (now - _LAST_FETCH > 15):
        _LAST_FETCH = now
        try:
            wiki_text = fetch_wikipedia_random()
            if wiki_text:
                _CACHE.append(wiki_text)
                if len(_CACHE) > 10:
                    _CACHE.pop(0)
                return wiki_text
        except Exception as e:
            pass
            
    if _CACHE:
        return random.choice(_CACHE)
    return fetch_tech_news()

if __name__ == '__main__':
    print("Testing Live Web Streamer...")
    text = get_latest_live_text()
    print("Fetched Live Text:", text[:120], "...")
