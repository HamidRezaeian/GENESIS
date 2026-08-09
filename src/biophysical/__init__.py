"""biophysical — Project GENESIS whole-neuron cell simulation.

Phase structure
---------------
  0a  Core structure, morphology, passive membrane  (this package)
  0b  Voltage-gated ion channels, action potentials
  0c  Synaptic machinery
  0d  Calcium dynamics and intracellular signalling
  0e  Gene expression: DNA → mRNA → protein
  0f  Organelles (mitochondria, ER, cytoskeleton …)
  0g  Metabolism and energy budget
  0h  Cell division (mitosis / apoptosis)
  0i  Full integration and validation

Public API
----------
  from biophysical import NeuronCell
  cell = NeuronCell.build_l5_pyramidal()
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("genesis")
except PackageNotFoundError:
    __version__ = "0a-dev"

from biophysical.neuron_cell import NeuronCell

__all__ = ["NeuronCell"]
