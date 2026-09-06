# Live Defense Session Preparation Guide (30-Minute Defense)

This document prepares you to defend every number, formula, code line, and strategic recommendation in the 30-minute live defense session.

---

## PART A: TOKENIZER AUDIT DEFENSE

### Q1: What is a tokenizer and what is a token?
* **Answer**: A tokenizer is a deterministic algorithm and lookup table that converts a sequence of raw characters into integer indices (token IDs) for a neural network, and vice versa. A token is the atomic unit of text corresponding to a single vocabulary entry. It can be a whole word, a subword fragment, a single character, or an individual byte.

### Q2: Why can one word become multiple tokens?
* **Answer**: Subword tokenizers (like Byte-Pair Encoding or WordPiece) have finite vocabularies (e.g. 50k–250k). High-frequency words get single tokens. Rare words, complex inflected words, or text written in scripts under-represented in the training data cannot be matched as full words. The tokenizer is forced to break them down into smaller subword morphemes, individual characters, or raw UTF-8 bytes.

### Q3: Why is lower fertility generally better?
* **Answer**: Two reasons:
  1. **Context Window Efficiency**: Models have hard context length limits (e.g. 4096 tokens). Lower fertility packs more semantic information into the window.
  2. **Latency**: Attention computation during prefill scales quadratically, and decode generation runs autoregressively step-by-step. Fewer tokens mean faster prefill and fewer autoregressive steps.

### Q4: Why doesn’t 5.89× fertility imply 5.89× higher serving cost?
* **Answer**: Because serving cost is not linearly proportional to prompt token count:
  1. **Prefill vs. Decode Asymmetry**: Prompt tokens are processed during prefill in parallel, compute-bound matrix multiplications (taking a few milliseconds). Generation decode is sequential and memory-bandwidth bound (taking dozens of milliseconds per token).
  2. **Batching Amortization**: Model weight loading memory bandwidth is amortized across all concurrent sequences in a batch.
  3. **Output Length Dominance**: In typical applications, generation length dominates perceived latency and GPU time. A longer prompt with a short generation costs vastly less than a long generation.

### Q5: Why is `words = line.split(" ")` an unambiguous code bug?
* **Answer**: `split(" ")` splits strictly on single space characters `' '`. If two spaces occur in succession, it outputs an empty string `""` as a list element. In `eng_sample.txt` line 7 (`books  in`) and `hin_sample.txt` line 10 (`किताबें  अलमारी`), double spaces occur. This inflated `len(words)` and artificially deflated reported fertility. Replacing it with `line.split()` strips empty strings, shifting English fertility from 1.2652 to 1.2831 (+0.0179) and Hindi from 7.4485 to 7.5985 (+0.1500).

### Q6: Why is `line.lower()` harmless on Hindi, but asymmetric on English?
* **Answer**: Brahmic scripts (Devanagari, Tamil, Kannada) are unicameral—they have no concept of uppercase or lowercase letters. In our isolation experiment, running Hindi with and without `lower()` yielded an **exact delta of 0.0000**. On English, `gpt2` has distinct tokens for capitalized vs. lowercase words, so lowercasing shifted English fertility by -0.0359 (-2.84%).

### Q7: Why is `tokens/word` flawed for cross-lingual comparisons? What does your chosen denominator hold constant?
* **Answer**:
  - `tokens/word` holds whitespace boundaries constant. But languages structure grammar differently: Tamil and Kannada are agglutinative and fuse prepositions and case suffixes into single words (16,775 words in Tamil vs. 21,901 in English for identical text). This unfairly shrinks the denominator for Dravidian languages.
  - `tokens/byte` holds raw digital storage constant, but UTF-8 assigns 1 byte to ASCII and 3 bytes to Indic characters, creating an opposite 3x artificial bias.
  - **Our Chosen Metric**: **Tokens per Parallel Sentence**. It holds **semantic information content** constant. Because LLM interactions are fundamentally about exchanging semantic information, parallel sentences provide the only unbiased cross-lingual denominator.

### Q8: How did you disprove REPORT_v0's claim that Hindi fertility is an inherent property of the script?
* **Answer**: On the exact same 1,012 FLORES parallel sentences, `gpt2` produced 7.42× more tokens per sentence for Hindi and 15.54× for Tamil because its vocabulary is English-centric. When we tested `IndicBERTv2` (an Indic-specialized tokenizer), the ratio dropped to **1.17× for Hindi**, **1.05× for Tamil**, and **1.10× for Kannada**. This proves high fertility was an artifact of vocabulary allocation, not the script.

---

## PART B: CAPACITY RECONCILIATION DEFENSE

### Q9: Re-derive the exact KV cache bytes per token live.
* **Derivation**:
  $$\text{KV Bytes / Token} = 2 \times L \times H_{KV} \times d_h \times \text{bytes per element}$$
  - $2$: Storing Key (K) and Value (V) tensors.
  - $L = 28$ layers.
  - $H_{KV} = 8$ heads (Grouped-Query Attention).
  - $d_h = 128$ dimensions per head.
  - $\text{bytes per element} = 2$ (fp16).
  $$\text{KV Bytes / Token} = 2 \times 28 \times 8 \times 128 \times 2 = \mathbf{114,688 \text{ bytes}} = \mathbf{112.0 \text{ KiB}}$$

### Q10: How many concurrent 4096-token sequences can fit on the L4 GPU? How did you resolve GB vs. GiB?
* **Derivation**:
  - Total GPU Memory: 24 GB. Usable budget at 0.92 = $22.08 \text{ GB}$.
  - Weights: $4.2\text{B} \times 2\text{ bytes} = 8.40\text{ GB}$.
  - Non-KV Runtime Overhead: $1.60\text{ GB}$.
  - Available KV Cache Pool = $22.08 - 8.40 - 1.60 = \mathbf{12.08 \text{ GB}} = 12,080,000,000\text{ bytes}$.
  - Maximum Tokens = $12,080,000,000 / 114,688 = 105,329.2\text{ tokens}$.
  - Maximum 4096-token sequences = $105,329.2 / 4096 = \mathbf{25.72 \implies 25 \text{ sequences}}$ (Floor).
* **Disambiguation**:
  - Binary GiB ($2^{30}$) would predict $29.18 \implies 29$ sequences.
  - In `bench_log.csv` at batch 24, `kv_cache_util` is reported as **0.93**. $24 / 0.93 = \mathbf{25.8\text{ sequences}}$, matching decimal GB ($25.72$) with 99.7% precision. Furthermore, batch 32 preempts exactly 7 sequences ($32 - 25 = 7$) and batch 48 preempts 23 ($48 - 25 = 23$). This proves the system uses **decimal GB**.

### Q11: What is the long-context throughput anomaly and its mechanism?
* **Answer**: In the prompt 3584 sweep, throughput peaks at batch 24 (1607.4 tok/s), then drops to 1384.0 tok/s at batch 32 (-13.9%) and collapses to 1298.5 tok/s at batch 48 (-19.2%), while wall-clock time spikes from 61.16s to 151.41s (+147%).
* **Mechanism**: KV cache block exhaustion. The GPU can only hold 25 sequences of length 4096. Admitting 32 or 48 sequences forces the scheduler to preempt active sequences (7 at batch 32, 23 at batch 48). Resuming preempted sequences requires expensive prefill recomputations, causing execution bubbles and destroying throughput.

### Q12: What configuration change fixes the anomaly, and what is the predicted effect?
* **Answer**: Set `--max-num-seqs 24` in the serving configuration.
* **Predicted Effect**: Requests beyond 24 wait in the host queue. An incoming batch of 48 runs in two clean, non-preempting waves of 24.
  - Wall-clock time drops from 151.41s to $2 \times 61.16\text{s} = \mathbf{122.32\text{s}}$ (**19.2% faster**).
  - Preemptions drop from **23 to 0**.
  - Effective throughput increases from 1298.5 to **1607.4 tok/s (+23.8%)**.

### Q13: What column did REPORT_v0 misread, and what was the formula?
* **Answer**: It misread **`reported_tok_s`**.
* **Formula**:
  $$\text{reported\_tok\_s} = \frac{\text{num\_requests} \times (\text{prompt\_len} + \text{gen\_len})}{\text{wall\_clock\_s}}$$
* It counted prompt tokens as generated throughput. Because prompt tokens are processed during prefill in parallel at compute-bound speeds, long prompts artificially inflate the number. In reality, decode throughput was lower for long prompts.

### Q14: Derive honest goodput for Batch 24 in two independent ways. Why do they disagree?
* **Method 1 (End-to-End Output Goodput)**:
  $$\text{Goodput}_1 = \frac{\text{batch} \times \text{gen\_len}}{\text{wall\_clock\_s}} = \frac{24 \times 512}{61.16\text{s}} = \mathbf{200.92 \text{ gen tok/s}}$$
* **Method 2 (Steady-State Decode from ITL)**:
  $$\text{Goodput}_2 = \frac{\text{batch}}{\text{ITL (s)}} = \frac{24}{0.09607\text{s}} = \mathbf{249.82 \text{ gen tok/s}}$$
* **Why they differ**: Method 1 amortizes the prefill phase (TTFT p50 = 500.5 ms) and request tail latency over the full 61.16s runtime. Method 2 measures pure steady-state generation speed during active decode.

---

## PART C: STRATEGIC DECISION DEFENSE

### Q15: Why did you recommend Option C (Prompt Engineering) over Option A (SFT) and Option B (Rewriter)?
* **Answer**:
  1. **Reviewer Bottleneck**: 1 reviewer for 10 hours/week over 2 weeks = **20 total review hours**. At 3 minutes/response, the reviewer can evaluate at most **400 total responses**.
  2. **Language Coverage Mismatch**: The reviewer only speaks Hindi and Kannada. Tamil, Telugu, Bengali, and Marathi have **0% reviewer coverage**.
  3. **Option A (SFT) Failure**: An 18,000-pair synthetic SFT dataset would be 97.8% unverified, and 100% unverified in 4 languages. Unsupervised synthetic text in Indic languages frequently introduces offensive/inappropriate pronoun and honorific regressions (*tu* vs *aap*).
  4. **Option B (Rewriter) Failure**: Adds 3–5 seconds of secondary decode latency, consumes 2 GB VRAM plus KV cache, and doubles production failure modes.
  5. **Option C Advantages**: Zero latency/VRAM overhead, Day-1 testable, zero risk of catastrophic forgetting, and allows 100% of our 400-sample reviewer bandwidth to be focused on perfecting few-shot exemplars and persona prompts.

### Q16: What is your Day-1 experiment and Kill Criterion?
* **Day-1 Experiment**: Curate 5 high-quality culturally authentic colloquial exemplars each for Hindi and Kannada with the reviewer; evaluate 50 standard prompts; score on 1–5 Likert scale for naturalness and honorific safety.
* **Kill Criterion & Deadline**: By **Day 8 (End of Week 1)**, if blind A/B win-rate against current formal outputs is $< 60\%$ or safety regressions exceed 3%, kill the casualization initiative and preserve standard polite outputs.
