#!/usr/bin/env python
"""
سه diagnostic کلیدی (توصیه Opus):
1. eligibility_trace.sum() بعد از اولین spike → باید > 0
2. M_t.mean() در طول training → باید non-zero و با variance
3. weight_delta.max() در هر update → باید > 1e-10
"""

import numpy as np

def run_three_diagnostics():
    print("=" * 70)
    print("Three Critical Diagnostics (Opus recommendation)")
    print("=" * 70)
    
    # Setup: small network
    n_in, n_hid, n_out = 10, 20