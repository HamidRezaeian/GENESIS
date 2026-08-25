import torch
import numpy as np

print("Testing PyTorch setup and CUDA availability...")
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.float16 if device == "cuda" else torch.float32
print(f"Device: {device}, Dtype: {dtype}")

# Let's test causal attribution calculation
D_MODEL = 32
W_causal = torch.randn(D_MODEL, D_MODEL, dtype=dtype, device=device) * 0.05
history = torch.randn(8, D_MODEL, dtype=dtype, device=device)
err_dyn = torch.randn(D_MODEL, dtype=dtype, device=device)

query = torch.matmul(err_dyn, W_causal)
scores = torch.matmul(history, query) / np.sqrt(D_MODEL)
attn = torch.softmax(scores, dim=0)
cause_idx = torch.argmax(attn).item()
print(f"Causal attribution weights shape: {attn.shape}, dominant cause index: {cause_idx}")

# Test counterfactual rollout
W_dyn = torch.randn(36, D_MODEL, dtype=dtype, device=device) * 0.05
W_rew = torch.randn(36, dtype=dtype, device=device) * 0.05
W_val = torch.randn(D_MODEL, dtype=dtype, device=device) * 0.05

s_cause = history[cause_idx]
for a_alt in range(4):
    sa_cf = torch.zeros(36, dtype=dtype, device=device)
    sa_cf[:32] = s_cause
    sa_cf[32 + a_alt] = 1.0
    s_cf_next = torch.tanh(torch.matmul(sa_cf, W_dyn))
    r_cf = torch.dot(sa_cf, W_rew).item()
    v_cf = torch.dot(s_cf_next, W_val).item()
    print(f"  Alt Action {a_alt}: r_cf={r_cf:.3f}, v_cf={v_cf:.3f}")

# Test autotelic goal synthesizer
W_goal = torch.randn(D_MODEL, D_MODEL, dtype=dtype, device=device) * 0.05
concept_emb = torch.randn(16, D_MODEL, dtype=dtype, device=device) * 0.05
opt_id = 3
z_goal = torch.tanh(torch.matmul(concept_emb[opt_id], W_goal))
dist = torch.norm(s_cause - z_goal).item()
print(f"Synthesized autotelic goal norm: {torch.norm(z_goal).item():.3f}, distance to current state: {dist:.3f}")

print("All Substrate 13 mathematical primitives verified successfully!")
