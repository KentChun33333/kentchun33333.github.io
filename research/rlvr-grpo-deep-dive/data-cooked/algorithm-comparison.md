# Algorithm Comparison: GRPO vs PPO vs DPO in Reasoning RL

| Architectural Dimension | Proximal Policy Optimization (PPO) | Group Relative Policy Optimization (GRPO) | Direct Preference Optimization (DPO) |
|---|---|---|---|
| **Active Networks During Training** | Actor ($\pi_\theta$) + Critic ($V_\phi$) + Reference ($\pi_{\text{ref}}$) | **Actor ($\pi_\theta$) + Reference ($\pi_{\text{ref}}$)** | Actor ($\pi_\theta$) + Reference ($\pi_{\text{ref}}$) |
| **VRAM Consumption** | $2.0\times$ (Actor + Value Model) | **$1.0\times$ (Actor Only, Critic-Free)** | $1.0\times$ (Actor Only) |
| **Advantage Estimation** | GAE: $\hat{A}_t = \sum (\gamma \lambda)^l \delta_{t+l}^V$ | **Group Normalized: $A_i = \frac{r_i - \mu_G}{\sigma_G}$** | N/A (Implicit Bradley-Terry) |
| **Reward Signal Source** | Learned Neural Reward Model (RM) | **Programmatic Ground Truth (Compilers, Unit Tests)** | Static Offline Human Preference Pairs |
| **Online Exploration** | Yes (Generates trajectories on-policy) | **Yes (Generates groups of $G$ rollouts on-policy)** | No (Offline supervised pairs only) |
| **Vulnerability to Reward Hacking** | High (Exploits learned RM bias/length) | **Zero for accuracy; bounded for format** | Moderate (Distribution shift) |
| **Multi-Step Deductive Search** | Unstable (Critic fails on sparse final rewards) | **Highly Stable (Group normalization absorbs variance)** | Incapable (Cannot search intermediate steps) |
| **Effective Batch Sampling** | Single rollout per query | **Group size $G \in [4, 16]$ per query** | Pairwise $(y_w, y_l)$ |
| **Ideal Deployment Scenario** | Dense conversational alignment | **Complex Math, SWE, Logic, and Code Reasoning** | Simple conversational style tuning |
