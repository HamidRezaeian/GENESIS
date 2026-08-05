# Architecture Design: Option 3 (Neuroevolution)

## 1. Overview
This document outlines the transition to Neuroevolution as the primary mechanism for adaptive behavior, abandoning in-lifetime weight updates.

## 2. Core Mechanism
The system will rely on evolutionary algorithms to optimize fixed network weights across generations. Organisms will express static SNN parameters throughout their lifespan.

## 3. Genetic Representation
Synaptic weights and network topologies will be encoded directly into the organism's genome, subject to crossover and mutation during reproduction.

## 4. Advantages
* Leverages existing and tested evolutionary infrastructure.
* Bypasses the instability of in-lifetime learning.
* Simplifies organism simulation (no runtime weight updates needed).

## 5. Potential Challenges
* Slower convergence compared to gradient-based methods.
* Requires well-designed fitness functions to shape complex behavior effectively.

## 6. Implementation Plan
1. Define genomic encoding for SNN weights.
2. Build decoder for phenotype expression at birth.
3. Update evolutionary operators to handle SNN traits.
4. Define fitness benchmarks for evolutionary validation.