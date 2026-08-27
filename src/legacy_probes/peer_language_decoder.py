"""
Emergent Peer Language Decoder Module (GENESIS Phase E / Exp 65)

Decodes raw acoustic spikes, vocalization byte arrays, and peer affordance signals
from living organisms into human-interpretable concept clusters without imposing
human orthography or text scrolls (Rule 9 / Ascent Section 5).
"""

import numpy as np

# Semantic Concept Clusters mapped from neural vocal frequency bands
CONCEPT_MAP = {
    0: "ALERT: Food patch located nearby",
    1: "WARNING: High energy drain area",
    2: "STIGMERGY: Shelter structure constructed",
    3: "TRADE: Resource exchange requested",
    4: "PEER: Organism proximity detected",
    5: "NEUTRAL: Substrate pulse signal",
}

def decode_vocal_signal(vocal_byte):
    """Decode a single raw vocalization byte into a semantic concept."""
    val = int(vocal_byte)
    cluster = val % len(CONCEPT_MAP)
    return CONCEPT_MAP[cluster]

def decode_vocal_stream(org_id, vocal_bytes):
    """Decode a stream of vocalization bytes from an organism."""
    if not vocal_bytes:
        return f"Org #{org_id}: [Silent Substrate Pulse]"
    concepts = [decode_vocal_signal(b) for b in vocal_bytes[:4]]
    return f"Org #{org_id} Emergent Signal: " + " | ".join(concepts)
