# SecureCodeAI: A Neuro-Symbolic Agent for Secure Code Generation and Repair

**Author**: Ansh Raj Rath  
**Affiliation**: Amrita School Of Artificial Intelligence, Amrita Vishwa Vidyapeetham, Coimbatore, India

**Abstract**
Large Language Models (LLMs) have demonstrated impressive capabilities in code generation but often struggle with security vulnerabilities. In this work, we present **SecureCodeAI**, a neuro-symbolic agentic framework that integrates LLMs with formal verification tools to enhance the security of generated code. We evaluate our approach on industry-standard benchmarks including SWE-bench, CyberSecEval 3, and PySecDB. We demonstrate that while static analysis tools like Bandit and Semgrep provide a baseline, our agentic approach offers superior context-aware detection and repair capabilities. We also present an ablation study analyzing the impact of symbolic feedback loops on repair quality.

## 1. Introduction
The proliferation of AI-generated code has raised concerns about the introduction of security vulnerabilities. Traditional Static Application Security Testing (SAST) tools often suffer from high false-positive rates and lack the semantic understanding to fix complex logic errors. SecureCodeAI addresses these limitations by employing a "Speculator-Verifier" architecture, where an LLM generates security contracts and a symbolic execution engine (CrossHair) verifies them.

## 2. Methodology
Our framework consists of three main components:
1.  **Scanner Agent (Neuro)**: Utilizes `Qwen2.5-Coder-1.5B-Instruct` to identify potential vulnerabilities and propose initial fixes.
2.  **Speculator Agent (Symbolic Bridge)**: Translates vulnerability hypotheses into formal Python contracts (using `icontract`).
3.  **SymBot (Symbolic Verifier)**: Executes `crosshair` to mathematically prove the presence or absence of a vulnerability, providing feedback to the Scanner.

## 3. Evaluation Setup
We conducted a comprehensive evaluation using the following benchmarks:
-   **SWE-bench**: Evaluates real-world software engineering capabilities.
-   **CyberSecEval 3**: Assesses the model's propensity to generate harmful code.
-   **PySecDB**: A dataset of real-world Python security commits.

All experiments were conducted using the Hugging Face Inference API for the Qwen model.

## 4. Results and Analysis

### 4.1 Vulnerability Detection
We compared SecureCodeAI against two baselines: Bandit and Semgrep.
-   **Bandit**: Identified 9 high-severity and 11 medium-severity issues in our test set.
-   **Semgrep**: Failed to flag issues with the default security profile, highlighting the need for custom rule-tuning.
-   **SecureCodeAI**: Successfully identified injection vulnerabilities in PySecDB samples, providing detailed explanations and fixes in addition to detection.

### 4.2 Repair Quality (Ablation Study)
We analyzed the impact of the neuro-symbolic feedback loop.
-   **Vanilla LLM**: Often generated "plausible looking" but incorrect fixes (e.g., ineffective sanitization).
-   **Neuro-Symbolic**: The symbolic feedback mechanism provided failed counter-examples, forcing the LLM to refine its patch until the contract was satisfied. This resulted in a higher rate of functionally correct and secure repairs.

## 5. Conclusion
SecureCodeAI demonstrates the potential of combining the creative generative power of LLMs with the rigor of formal methods. Our evaluation shows that this hybrid approach outperforms traditional static analysis in distinct ways, offering a path toward more reliable AI-assisted software development.

## 6. Future Work
Future iterations will focus on scaling the symbolic execution to handle larger codebases and integrating the GitHub Copilot API for a direct commercial baseline comparison.

## References
[1] SWE-bench: Can Language Models Resolve Real-World GitHub Issues?
[2] Meta CyberSecEval 3: A Benchmark for Evaluating Cybersecurity Risks of LLMs.
[3] PySecDB: A Real-world Python Security Commit Dataset.
