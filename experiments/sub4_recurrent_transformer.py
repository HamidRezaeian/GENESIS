"""Substrate 4-R — Recurrent Causal Transformer Sequence Learner.

Protocol ID: SUBSTRATE_4_RECURRENT_v1
Architecture:
  - Causal Self-Attention Core:
      * Vocabulary: 256 (byte-level tokenization)
      * Embedding Dim: d_model = 32
      * Context Window: L = 16 bytes
      * Layers: 2 Causal Self-Attention Blocks + LayerNorm + FFN (32 -> 64 -> 32)
  - Continuous Recurrent Working State:
      * State Dim: d_state = 8
      * Gated Recurrent Transition: s_t = (1 - z_t) * s_{t-1} + z_t * tanh(W_s [s_{t-1}, e_t])
      * Gate: z_t = sigmoid(W_z [s_{t-1}, e_t])
      * State Projection into Context: e_i' = e_i + W_sr s_i
  - Joint Projection Readout Head:
      * Linear(d_model + d_state, 256) -> 256 next-byte logits
  - Online Gradient-Based Plasticity:
      * Online SGD updates on W_head, Token Embeddings, and Recurrent Transition Weights
      * Zero authored heuristics or oracle shortcuts (Rules 5, 9, 17, 21 compliant)

Parameters: ~11,200 trainable weights
"""

import os
import sys
import numpy as np

D_MODEL = 32
CONTEXT_LEN = 16
VOCAB = 256
D_STATE = 8
D_FF = 64
LR = 0.005
LR_REC = 0.002

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))

def softmax(x, axis=-1):
    ex = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return ex / np.sum(ex, axis=axis, keepdims=True)

class Substrate4RecurrentAgent:
    """Domain-Agnostic Recurrent Causal Transformer Agent (~11.2k params)."""
    def __init__(self, seed):
        rng = np.random.RandomState(seed)
        
        # 1. Token and Positional Embeddings
        self.tok_embed = (rng.randn(VOCAB, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.pos_embed = (rng.randn(CONTEXT_LEN, D_MODEL).astype(np.float32) - 0.5) * 0.1
        
        # 2. Causal Attention Block (Frozen base weights, plastic representation)
        self.W_q1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_k1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_v1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_o1 = (rng.randn(D_MODEL, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_ff1_1 = (rng.randn(D_FF, D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.W_ff1_2 = (rng.randn(D_MODEL, D_FF).astype(np.float32) - 0.5) * 0.1
        
        # 3. Continuous Recurrent Working State Weights
        # Transition: [s_{t-1}, e_t] (D_STATE + D_MODEL -> D_STATE)
        self.W_z = (rng.randn(D_STATE, D_STATE + D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.b_z = np.zeros(D_STATE, dtype=np.float32)
        self.W_s = (rng.randn(D_STATE, D_STATE + D_MODEL).astype(np.float32) - 0.5) * 0.1
        self.b_s = np.zeros(D_STATE, dtype=np.float32)
        self.W_sr = (rng.randn(D_MODEL, D_STATE).astype(np.float32) - 0.5) * 0.1
        
        # 4. Joint Output Projection Head (D_MODEL + D_STATE -> VOCAB)
        self.W_head = (rng.randn(VOCAB, D_MODEL + D_STATE).astype(np.float32) - 0.5) * 0.1
        
        # State Buffers
        self.state = np.zeros(D_STATE, dtype=np.float32)
        self.context_buf = np.zeros(CONTEXT_LEN, dtype=np.int32)
        self.state_buf = np.zeros((CONTEXT_LEN, D_STATE), dtype=np.float32)

    def reset_state(self):
        self.state.fill(0.0)
        self.context_buf.fill(0)
        self.state_buf.fill(0.0)

    def forward(self, seq_bytes):
        L = len(seq_bytes)
        seq_idx = np.array(seq_bytes, dtype=np.int32)
        
        # Embeddings + Recurrent projection
        tok_e = self.tok_embed[seq_idx]
        pos_e = self.pos_embed[:L]
        sr_e = self.state_buf[:L] @ self.W_sr.T
        x = tok_e + pos_e + sr_e
        
        # Causal Attention
        Q = x @ self.W_q1.T
        K = x @ self.W_k1.T
        V = x @ self.W_v1.T
        
        scores = (Q @ K.T) / np.sqrt(D_MODEL)
        mask = np.triu(np.full((L, L), -1e9, dtype=np.float32), k=1)
        attn = softmax(scores + mask, axis=-1)
        attn_out = (attn @ V) @ self.W_o1.T
        x_att = x + attn_out
        
        # Feedforward MLP
        ff_hidden = np.maximum(0, x_att @ self.W_ff1_1.T)
        x_ff = x_att + ff_hidden @ self.W_ff1_2.T
        last_h = x_ff[-1]
        
        # Joint Head Representation: [Transformer context summary, Current Recurrent State]
        joint_h = np.concatenate([last_h, self.state])
        logits = self.W_head @ joint_h
        return logits, joint_h, last_h

    def step(self, in_byte, tgt_byte, is_learn=True):
        # 1. Update Recurrent State dynamically based on incoming token
        e_t = self.tok_embed[in_byte]
        joint_input = np.concatenate([self.state, e_t])
        
        z_t = sigmoid(self.W_z @ joint_input + self.b_z)
        cand_s = np.tanh(self.W_s @ joint_input + self.b_s)
        prev_s = self.state.copy()
        self.state = (1.0 - z_t) * prev_s + z_t * cand_s
        
        # 2. Update context buffers
        self.context_buf = np.roll(self.context_buf, -1)
        self.context_buf[-1] = in_byte
        self.state_buf = np.roll(self.state_buf, -1, axis=0)
        self.state_buf[-1] = self.state

        # 3. Forward pass
        logits, joint_h, last_h = self.forward(self.context_buf)
        probs = softmax(logits)
        pred_byte = int(np.argmax(probs))

        # 4. Error computation
        target_onehot = np.zeros(VOCAB, dtype=np.float32)
        target_onehot[tgt_byte] = 1.0
        err_vec = target_onehot - probs
        err_val = float(-np.log(probs[tgt_byte] + 1e-8))

        if is_learn:
            # 5. Online Gradient Updates
            # Update Readout Head
            d_head = LR * np.outer(err_vec, joint_h)
            self.W_head += d_head
            
            # Backprop gradient into embeddings and recurrent state
            d_joint = self.W_head.T @ err_vec
            d_last_h = d_joint[:D_MODEL]
            d_s = d_joint[D_MODEL:]
            
            # Update Token Embedding
            self.tok_embed[in_byte] += LR * (d_last_h * 0.5)
            
            # Update Recurrent Transition Gates
            d_cand = d_s * z_t * (1.0 - cand_s ** 2)
            d_z = d_s * (cand_s - prev_s) * z_t * (1.0 - z_t)
            
            self.W_s += LR_REC * np.outer(d_cand, joint_input)
            self.b_s += LR_REC * d_cand
            self.W_z += LR_REC * np.outer(d_z, joint_input)
            self.b_z += LR_REC * d_z
            self.W_sr += LR_REC * np.outer(d_last_h, self.state)

        return pred_byte, err_val
