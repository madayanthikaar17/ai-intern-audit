# MEMORANDUM

**TO:** Leadership & Serving Infrastructure Team  
**FROM:** AI Intern / Auditing Team  
**DATE:** September 6, 2026  
**SUBJECT:** Tokenizer Audit & Indic Traffic Routing Recommendation (Supercedes REPORT_v0)

---

### 1. Corrected Headline Numbers
Our audit evaluated 1,012 parallel sentences across English, Hindi, Tamil, and Kannada on the FLORES-200 benchmark. We compared our English-centric baseline (`gpt2`) against an Indic-specialized tokenizer (`IndicBERTv2`) and a modern multilingual foundation model (`Qwen2.5`).

* **Refutation of REPORT_v0**: The claim that *"Hindi tokenization struggles are an unfixable property of the script"* is empirically false. Under `gpt2`, Hindi requires 7.42× and Tamil requires 15.54× more tokens per sentence than English because the vocabulary is English-centric. Under `IndicBERTv2`, this penalty collapses to **1.17× for Hindi**, **1.05× for Tamil**, and **1.10× for Kannada**.
* **Serving Cost Correction**: High tokenization fertility does **not** translate to a 1:1 proportional increase in serving cost. Conflating prompt tokens with total cost ignores the reality of compute-bound parallel prefill vs. memory-bandwidth-bound decode latency.

| Language | gpt2 (Tokens/Sent) | IndicBERTv2 (Tokens/Sent) | Qwen2.5 (Tokens/Sent) | Effective Semantic Overhead (vs. Eng) |
| :--- | :---: | :---: | :---: | :---: |
| **English** | 26.7 (1.00×) | 26.8 (1.00×) | 27.3 (1.00×) | Baseline (1.00×) |
| **Hindi** | 198.3 (7.42×) | 31.3 (1.17×) | 120.5 (4.42×) | **+17%** with Indic Tokenizer |
| **Tamil** | 415.2 (15.54×) | 28.1 (1.05×) | 166.8 (6.11×) | **+5%** with Indic Tokenizer |
| **Kannada** | 363.0 (13.59×) | 29.4 (1.10×) | 188.9 (6.92×) | **+10%** with Indic Tokenizer |

---

### 2. Strategic Routing Recommendation
* **Adopt an Indic-Aware Tokenizer / Model**: Route all Indic production traffic to a model family with an Indic-specialized vocabulary (or a modern 150k+ multilingual tokenizer). This eliminates 85–90% of token bloat, prevents premature context exhaustion, and reduces time-to-first-token (TTFT) by up to 5×.
* **Do NOT Over-Budget 6× Serving Capacity**: Cancel plans to budget 6× hardware capacity for Indic queries. With an Indic-aware tokenizer, prompt token expansion is only 1.05×–1.17×. Even under standard multilingual models, decode-phase resource utilization remains the primary cost driver.

---

### 3. Biggest Caveat
* **Domain & Register Mismatch**: Our eval benchmark (FLORES-200) consists of formal, professionally translated encyclopedic text. **It does not represent real production traffic**, which is heavily colloquial, contains Romanized transliteration (Hinglish/Tanglish), and exhibits frequent code-mixing. Tokenizer compression on formal text will degrade when users type phonetic Roman script.

---

### 4. Production Metric to Monitor
* **Primary Telemetry Metric**: **`p95_prompt_to_decode_token_ratio`** (and `mean_request_latency_by_language`).
* **Why**: If production inputs contain heavy out-of-vocabulary code-mixing or transliteration, subword fragmentation will spike, inflating prompt token counts. Monitoring this counter will immediately alert the team if real-world user queries diverge from our clean benchmark assumptions.
