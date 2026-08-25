import re

def patch_brain():
    with open('src/genesis/server/genesis_pytorch_brain.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update Init
    old_init = '''        self.W_transfer = self._rand_mat(self.num_concepts, self.num_concepts, 0.05)
        self.option_fisher_diag = {'''
        
    new_init = '''        self.W_transfer = self._rand_mat(self.num_concepts, self.num_concepts, 0.05)
        self.W_concept_to_symbol = self._rand_mat(self.num_concepts, VOCAB_SIZE, 0.05)
        self.option_fisher_diag = {
            "W_concept_to_symbol": torch.zeros((self.num_concepts, VOCAB_SIZE), dtype=self.dtype, device=self.device),'''
            
    content = content.replace(old_init, new_init)

    old_anchor = '''        self.option_anchor_weights = {
            "W_concept_value": self.W_concept_value.clone(),
            "concept_embeddings": self.concept_embeddings.clone()
        }'''
    new_anchor = '''        self.option_anchor_weights = {
            "W_concept_value": self.W_concept_value.clone(),
            "concept_embeddings": self.concept_embeddings.clone(),
            "W_concept_to_symbol": self.W_concept_to_symbol.clone()
        }'''
    content = content.replace(old_anchor, new_anchor)

    # 2. run_hierarchical_mcts
    old_run = '''        # Condition Low Level on Concept Context
        concept_emb = self.concept_embeddings[opt_id]
        attn = torch.softmax(torch.matmul(concept_emb, self.W_opt_q.T), dim=-1)
        opt_ctx = torch.matmul(attn, self.W_opt_q)
        enriched_state = root_state + opt_ctx'''
        
    new_run = '''        # Condition Low Level on Concept Context
        concept_emb = self.concept_embeddings[opt_id]
        attn = torch.softmax(torch.matmul(concept_emb, self.W_opt_q.T), dim=-1)
        opt_ctx = torch.matmul(attn, self.W_opt_q)
        
        # Emit Symbol
        sym_logits = self.W_concept_to_symbol[opt_id]
        sym_probs = torch.softmax(sym_logits, dim=-1)
        emitted_symbol = torch.multinomial(sym_probs, 1).item()
        sym_emb = self.W_lang[emitted_symbol]
        
        enriched_state = root_state + opt_ctx + sym_emb'''
    content = content.replace(old_run, new_run)
    
    # 3. run_hierarchical_mcts returns emitted_symbol
    content = content.replace('"selected_action": np.argmax(ll_res["probs"])', '"selected_action": int(np.argmax(ll_res["probs"])),\\n            "emitted_symbol": emitted_symbol')
    
    # 4. update_hierarchical_experience 
    content = content.replace('def update_hierarchical_experience(self, s_curr_np, concept_id, action_id, reward, s_next_np, is_terminal=False):', 'def update_hierarchical_experience(self, s_curr_np, concept_id, symbol_id, action_id, reward, s_next_np, is_terminal=False):')
    
    old_low = '''        # Low Level Update (Physical environment reward)
        concept_emb = self.concept_embeddings[concept_id]
        attn = torch.softmax(torch.matmul(concept_emb, self.W_opt_q.T), dim=-1)
        opt_ctx = torch.matmul(attn, self.W_opt_q).cpu().numpy()
        enriched_s_curr = s_curr_np + opt_ctx'''
        
    new_low = '''        # Low Level Update (Physical environment reward)
        concept_emb = self.concept_embeddings[concept_id]
        attn = torch.softmax(torch.matmul(concept_emb, self.W_opt_q.T), dim=-1)
        opt_ctx = torch.matmul(attn, self.W_opt_q).cpu().numpy()
        sym_emb = self.W_lang[symbol_id].cpu().numpy()
        enriched_s_curr = s_curr_np + opt_ctx + sym_emb'''
    content = content.replace(old_low, new_low)
    
    content = content.replace('"entropy_gain": intrinsic_reward', '"entropy_gain": intrinsic_reward,\\n            "symbol": symbol_id')
    
    # 5. sleep_consolidation
    content = content.replace('def update_concept_weights(self, s_curr_np, concept_id, entropy_gain):', 'def update_concept_weights(self, s_curr_np, concept_id, symbol_id, entropy_gain):')
    content = content.replace('self.update_concept_weights(exp["s_curr"], exp["option"], exp["entropy_gain"])', 'self.update_concept_weights(exp["s_curr"], exp["option"], exp["symbol"], exp["entropy_gain"])')
    
    # 6. Checkpoints
    content = content.replace('"concept_embeddings": self.concept_embeddings.cpu().numpy(),\\n            "W_transfer": self.W_transfer.cpu().numpy(),', '"concept_embeddings": self.concept_embeddings.cpu().numpy(),\\n            "W_transfer": self.W_transfer.cpu().numpy(),\\n            "W_concept_to_symbol": self.W_concept_to_symbol.cpu().numpy(),')
    
    old_load = '''                self.W_transfer = torch.tensor(data["W_transfer"], dtype=self.dtype, device=self.device)
                self.option_anchor_weights["W_concept_value"] = self.W_concept_value.clone()
                self.option_anchor_weights["concept_embeddings"] = self.concept_embeddings.clone()'''
    new_load = '''                self.W_transfer = torch.tensor(data["W_transfer"], dtype=self.dtype, device=self.device)
                self.W_concept_to_symbol = torch.tensor(data["W_concept_to_symbol"], dtype=self.dtype, device=self.device)
                self.option_anchor_weights["W_concept_value"] = self.W_concept_value.clone()
                self.option_anchor_weights["concept_embeddings"] = self.concept_embeddings.clone()
                self.option_anchor_weights["W_concept_to_symbol"] = self.W_concept_to_symbol.clone()'''
    content = content.replace(old_load, new_load)
    
    # Write patched file
    with open('src/genesis/server/genesis_pytorch_brain.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched genesis_pytorch_brain.py for Substrate 12")

def patch_server():
    with open('src/genesis/server/brain_server.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Make step_once use hierarchical mcts
    old_step = '''        mcts_info = self.brain.run_mcts(s_curr, self.policy_mode)

        probs = np.array(mcts_info["probs"], dtype=np.float64)
        probs /= (np.sum(probs) + 1e-9) # ensure sum is exactly 1.0 for np.random.choice
        action = int(self.brain.rng.choice(N_ACTIONS, p=probs))'''
        
    new_step = '''        mcts_info = self.brain.run_hierarchical_mcts(s_curr, self.policy_mode)
        
        # In Substrate 12, we get both option, action and emitted symbol
        probs = np.array(mcts_info["action_probs"], dtype=np.float64)
        probs /= (np.sum(probs) + 1e-9)
        action = int(self.brain.rng.choice(N_ACTIONS, p=probs))
        
        self.prev_option = mcts_info["selected_option"]
        self.prev_symbol = mcts_info.get("emitted_symbol", 0)'''
        
    content = content.replace(old_step, new_step)
    
    # Fix update_hierarchical_experience calls
    old_update = '''        is_term = (self.energy <= 0.0) or (event == "GOAL_SOLVED")
        metrics = self.brain.update_neural_weights(s_curr, action, reward, s_next, is_terminal=is_term, is_replay=False)'''
        
    new_update = '''        is_term = (self.energy <= 0.0) or (event == "GOAL_SOLVED")
        
        if hasattr(self, 'prev_option'):
            self.brain.update_hierarchical_experience(s_curr, self.prev_option, self.prev_symbol, action, reward, s_next, is_term)
            
        metrics = self.brain.update_neural_weights(s_curr, action, reward, s_next, is_terminal=is_term, is_replay=False)'''
    content = content.replace(old_update, new_update)

    with open('src/genesis/server/brain_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched brain_server.py for Substrate 12")

if __name__ == "__main__":
    patch_brain()
    patch_server()
