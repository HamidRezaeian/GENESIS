"""DEPRECATED (2026-07-13) — superseded by brain_io's self-describing checkpoint.

This module assumed a fixed-offset Phase-2 genome (`w_ih | w_ho | thresh | tau` blocks) and
byte-remapped it across `n_input/n_hidden/n_output` changes. The engine has long since moved to a
MARKER-based, variable-length genome (GENE_MARKER / NEURON_MARKER / RECEPTOR_MARKER) whose
connections decode as `dst % (N_IO + hidden_count)`. There is no faithful byte-remap across an
`N_IO` change for that encoding — the modulo entangles every connection — so offset migration here
would silently corrupt genomes.

The forward-compatibility problem is now solved differently and correctly (see `brain_io.py`):
Brain.npz carries an ENGINE FINGERPRINT, and on save a stale-layout file is ARCHIVED and rebuilt
automatically. A code change never requires a manual delete, and an incompatible checkpoint is never
loaded as if it were valid. Nothing imports this module; it is kept only as a redirect.
"""


def migrate_genomes(*args, **kwargs):
    raise NotImplementedError(
        "brain_migration.migrate_genomes is retired. Brain.npz is now self-describing and "
        "self-healing via brain_io.save_brain/load_brain (fingerprint + monotonic hall-of-fame); "
        "stale-layout checkpoints are archived and rebuilt automatically. See src/brain_io.py."
    )
