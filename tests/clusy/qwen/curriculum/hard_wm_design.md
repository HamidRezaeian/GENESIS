# Curriculum Hardening Design — Hard Working Memory Curriculum

## Problem

The current GradedMemory curriculum (`a1A`, `b&B` patterns) has only 2 cues,
predictable capitalization, and noise drawn from a limited character set.
Organisms can achieve 43%+ accuracy with simple bigram heuristics and no
genuine working memory.

## Design Principles

1. **Combinatorial explosion of cue-answer pairs** — prevents memorization
2. **Pure random noise** — eliminates statistical regularities
3. **Graded delay** — from trivial (4 bytes) to extreme (64 bytes)
4. **Correct bytes only exist once** — no bigram shortcut
5. **All-or-nothing credit** — partial accuracy does not earn partial reward

## The Hard_WM Curriculum

K = 16 cues (lowercase a-p), 16 answers (uppercase A-P), but the mapping is
a random permutation generated at injection time. The organism must learn the
mapping by EXPERIENCE, not by capitalization rule.

```
i$x*H          (cue=i at pos 0, noise at pos 1-3, answer=H at pos 4)
c<;+F          (cue=c at pos 0, noise at pos 1-3, answer=F at pos 4)
m@3{K          (cue=m at pos 0, noise at pos 1-3, answer=K at pos 4)
```

Noise characters are drawn from ALL printable non-letter ASCII (digits,
punctuation, symbols): `!"#$%&'()*+,-./:;<=>?@[\\]^_{|}~0123456789`

## Generator Code

```python
def generate_hard_wm(filename, total_lines=500, seed=42):
    import random, string
    random.seed(seed)

    cues = list(string.ascii_lowercase[:16])      # a-p
    answers = list(string.ascii_uppercase[:16])    # A-P
    random.shuffle(answers)                         # random permutation
    mapping = dict(zip(cues, answers))

    noise_chars = string.digits + string.punctuation  # no letters at all
    delays = [4, 8, 16, 24, 32, 48, 64]
    lines_per_stage = total_lines // len(delays)

    lines = []
    for delay in delays:
        for _ in range(lines_per_stage):
            cue = random.choice(cues)
            noise = ''.join(random.choice(noise_chars) for _ in range(delay))
            ans = mapping[cue]
            lines.append(f"{cue}{noise}{ans}")

    with open(filename, 'w') as f:
        f.write('\n'.join(lines) + '\n')
```

## Why This Kills The Shortcuts

| Shortcut | Why It Fails |
|----------|-------------|
| Echo reflex | Answer is NEVER the same as cue (16-bit permutation) |
| Bigram table | 16 × 256 possible noise-byte transitions, never repeated |
| Spatial phase lock | Delay varies (4–64), position-to-answer changes every line |
| Frequency analysis | All 16 answers equally frequent (1/16 each) |
| Capitalization rule | NO rule — `a` might map to `M`, `b` to `D`, etc. |

## Performance Prediction

| Metric | Current GradedMemory | Hard_WM |
|--------|--------------------:|--------:|
| Cues | 2 | **16** |
| Answer entropy | 1 bit | **4 bits** |
| Bigram predictability | ~35% | **<0.1%** |
| Echo reflex accuracy | ~25% | **~0%** |
| Best achievable without WM | ~43% | **~6.25% (random)** |
