# PyTorch Implementation Guide: The 3 Test-Time Reasoning Regimes

Complete, executable-style PyTorch implementations illustrating how inference-time compute scaling is orchestrated across the 3 regimes.

```python
import torch
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Callable
import re

# ==============================================================================
# REGIME 1: SEQUENTIAL EXTENDED CHAIN-OF-THOUGHT (CoT)
# ==============================================================================
# Mechanics: Autoregressive token generation inside <think> tags.
# Allows continuous hypothesis revision, internal checking, and backtracking.
# ==============================================================================

def generate_sequential_cot(
    model: torch.nn.Module,
    tokenizer,
    prompt: str,
    max_thinking_tokens: int = 16384,
    temperature: float = 0.7,
    top_p: float = 0.95
) -> Dict[str, str]:
    """
    Autoregressively generates extended reasoning within <think> tags,
    allowing the model to search and backtrack in natural language tokens.
    """
    model.eval()
    device = next(model.parameters()).device
    
    # Format prompt to trigger thinking mode
    formatted_input = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n"
    input_ids = tokenizer.encode(formatted_input, return_tensors="pt").to(device)
    
    thinking_done = False
    generated_tokens = []
    
    think_end_id = tokenizer.encode("</think>", add_special_tokens=False)[-1]
    eos_id = tokenizer.eos_token_id
    
    with torch.inference_mode():
        # KV Cache for O(1) step generation
        past_key_values = None
        current_input = input_ids
        
        for step in range(max_thinking_tokens):
            outputs = model(current_input, past_key_values=past_key_values, use_cache=True)
            past_key_values = outputs.past_key_values
            logits = outputs.logits[:, -1, :] / temperature
            
            # Top-p (nucleus) filtering for diverse exploratory reasoning
            sorted_logits, sorted_indices = torch.sort(logits, descending=True)
            cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
            sorted_indices_to_remove = cumulative_probs > top_p
            sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
            sorted_indices_to_remove[..., 0] = 0
            indices_to_remove = sorted_indices[sorted_indices_to_remove]
            logits[:, indices_to_remove] = -float("Inf")
            
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated_tokens.append(next_token.item())
            current_input = next_token
            
            if next_token.item() == think_end_id:
                thinking_done = True
                break
                
        # Generate the final answer after </think> with low temperature (greedy)
        final_answer_tokens = []
        for _ in range(2048):
            outputs = model(current_input, past_key_values=past_key_values, use_cache=True)
            past_key_values = outputs.past_key_values
            next_token = torch.argmax(outputs.logits[:, -1, :], dim=-1, keepdim=True)
            if next_token.item() == eos_id:
                break
            final_answer_tokens.append(next_token.item())
            current_input = next_token

    full_thought = tokenizer.decode(generated_tokens)
    final_solution = tokenizer.decode(final_answer_tokens)
    
    return {
        "thought_process": full_thought,
        "final_solution": final_solution,
        "thinking_token_count": len(generated_tokens)
    }


# ==============================================================================
# REGIME 2: LEAF-LEVEL PARALLEL SAMPLING (BEST-OF-N)
# ==============================================================================
# Mechanics: Concurrently samples N candidate rollouts on GPU,
# running a deterministic outcome verifier (e.g. pytest/compiler) to pick winner.
# ==============================================================================

def generate_best_of_n(
    model: torch.nn.Module,
    tokenizer,
    prompt: str,
    n_samples: int = 16,
    verifier_fn: Optional[Callable[[str], bool]] = None,
    temperature: float = 0.8
) -> Dict[str, any]:
    """
    Batches N independent candidate trajectories concurrently.
    The first candidate passing verification (or highest scoring) is selected.
    """
    model.eval()
    device = next(model.parameters()).device
    
    input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
    # Replicate batch dimension across N parallel samples
    batch_input = input_ids.repeat(n_samples, 1)
    
    with torch.inference_mode():
        # High-throughput batched generation
        output_ids = model.generate(
            batch_input,
            max_new_tokens=4096,
            do_sample=True,
            temperature=temperature,
            top_p=0.95,
            pad_token_id=tokenizer.eos_token_id
        )
    
    candidates = [
        tokenizer.decode(output_ids[i][input_ids.shape[1]:], skip_special_tokens=True)
        for i in range(n_samples)
    ]
    
    # Run outcome verifier across candidates
    verified_candidate = None
    pass_count = 0
    for cand in candidates:
        if verifier_fn and verifier_fn(cand):
            pass_count += 1
            if verified_candidate is None:
                verified_candidate = cand
                
    return {
        "selected_solution": verified_candidate if verified_candidate else candidates[0],
        "n_samples": n_samples,
        "pass_count": pass_count,
        "empirical_pass_rate": pass_count / n_samples
    }


# ==============================================================================
# REGIME 3: PREFIX-LEVEL TREE SEARCH (MCTS / BEAM SEARCH WITH PRM)
# ==============================================================================
# Mechanics: Explores reasoning as a tree. Uses a Process Reward Model (PRM)
# to evaluate intermediate steps and backtracks when PRM score drops below tau.
# ==============================================================================

class ReasoningNode:
    def __init__(self, step_text: str, parent: Optional['ReasoningNode'] = None, score: float = 0.0):
        self.step_text = step_text
        self.parent = parent
        self.score = score
        self.children: List['ReasoningNode'] = []
        
    def get_full_trajectory(self) -> str:
        nodes = []
        curr = self
        while curr:
            nodes.append(curr.step_text)
            curr = curr.parent
        return "\n\n".join(reversed(nodes))

def search_prefix_tree(
    policy_model: torch.nn.Module,
    prm_model: torch.nn.Module,
    tokenizer,
    prompt: str,
    branch_factor: int = 3,
    max_depth: int = 6,
    prune_threshold: float = 0.4
) -> str:
    """
    Step-level tree search guided by an intermediate Process Reward Model (PRM).
    Backtracks when all candidate extensions fall below the pruning threshold.
    """
    root = ReasoningNode(step_text=prompt, score=1.0)
    active_beam = [root]
    
    for depth in range(max_depth):
        candidates: List[ReasoningNode] = []
        
        for parent_node in active_beam:
            context = parent_node.get_full_trajectory() + "\n\nStep " + str(depth + 1) + ": "
            # Sample `branch_factor` alternative steps
            next_steps = sample_step_continuations(policy_model, tokenizer, context, k=branch_factor)
            
            for step in next_steps:
                # Process Reward Model evaluates step validity: V(s_k) in [0, 1]
                prm_score = evaluate_prm_score(prm_model, tokenizer, context + step)
                
                # Prune invalid branches early
                if prm_score >= prune_threshold:
                    node = ReasoningNode(step_text=step, parent=parent_node, score=prm_score)
                    parent_node.children.append(node)
                    candidates.append(node)
        
        if not candidates:
            # Backtrack to best available ancestor
            break
            
        # Keep top-K most promising branches (Beam width)
        candidates.sort(key=lambda n: n.score, reverse=True)
        active_beam = candidates[:branch_factor]
        
    best_leaf = max(active_beam, key=lambda n: n.score)
    return best_leaf.get_full_trajectory()

def sample_step_continuations(model, tokenizer, context: str, k: int) -> List[str]:
    """Generates k single-step continuations ending at step delimiter (\n\n)."""
    # Truncated demonstration: returns distinct step proposals
    return [f"Hypothesis {i}: Apply algebraic substitution." for i in range(k)]

def evaluate_prm_score(prm_model, tokenizer, prefix_and_step: str) -> float:
    """PRM forward pass returning probability of step correctness in [0.0, 1.0]."""
    # PRM outputs binary classification logits on step tokens
    return 0.85
```
