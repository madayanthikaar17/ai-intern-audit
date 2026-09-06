**# Lab Notebook -- AI Team Intern Assignment: The Audit**

**## Baseline Verification**

\- **\*\*Date\*\***: 2026-09-06

\- **\*\*Script\*\***: \`starter\_kit/fertility.py\` (unmodified)

\- **\*\*Data\*\***: \`starter\_kit/corpus\_sample/eng\_sample.txt\`, \`starter\_kit/corpus\_sample/hin\_sample.txt\`

\- **\*\*Tokenizer\*\***: \`gpt2\` (tiktoken)

\- **\*\*Baseline Result\*\***:

  - English: 1.27 tok/word, 0.226 tok/char

  - Hindi: 7.45 tok/word, 1.579 tok/char

  - Reported Ratio: 5.89x worse tokenization for Hindi

**---**

**# Experiment 1: Whitespace Splitting Bug (\`split(" ")\` vs \`split()\`)**

**## Hypothesis**

\`words = line.split(" ")\` in \`fertility.py\` splits strictly on single space characters. When lines contain multiple consecutive spaces (e.g. line 7 of \`eng\_sample.txt\` and line 10 of \`hin\_sample.txt\`), \`split(" ")\` generates empty strings \`""\` as items, inflating the word count \`len(words)\` and artificially deflating fertility. Replacing it with \`line.split()\` will eliminate phantom words and increase fertility.

**## Why I Thought This**

Inspecting \`starter\_kit/corpus\_sample/eng\_sample.txt\` line 7 revealed:

\`"Please keep the books  in the cupboard."\` (two spaces between \`books\` and \`in\`).

In Python, \`"books  in".split(" ")\` yields \`["books", "", "in"]\` (length 3), whereas \`"books  in".split()\` yields \`["books", "in"]\` (length 2).

**## Experiment**

Script: \`madayanthikaa/partA/audit/isolate\_bugs.py\`

Command:

\`\`\`bash

python madayanthikaa/partA/audit/isolate\_bugs.py

\`\`\`

**## Result**

\- **\*\*Before (\`split(" ")\`)\*\***:

  - \`eng\`: 1.2652 tok/word (reported rounded as 1.27)

  - \`hin\`: 7.4485 tok/word (reported rounded as 7.45)

  - Ratio: 5.8871x

\- **\*\*After (\`split()\`)\*\***:

  - \`eng\`: 1.2831 tok/word

  - \`hin\`: 7.5985 tok/word

  - Ratio: 5.9221x

\- **\*\*Delta\*\***:

  - \`eng\`: +0.0179 tok/word (+1.41%)

  - \`hin\`: +0.1500 tok/word (+2.01%)

  - Ratio: +0.0350x

**## Interpretation & Why This Proves the Claim**

The delta proves that \`split(" ")\` creates phantom empty-string tokens in the word list whenever whitespace is irregular, undercounting true fertility. The change strictly increases fertility across both corpora because the denominator \`len(words)\` was corrected downward to genuine words.

**## Conclusion**

Confirmed: **\*\*Real Code Bug\*\***.

**---**

**# Experiment 2: Conceptual Metric Distinction -- Line-Weighted vs Aggregate Fertility**

**## Hypothesis**

\`fertility.py\` computes \`per\_line\_fertility.append(len(tokens) / len(words))\` and returns \`sum(per\_line\_fertility) / n\`.

This is mathematically valid as a **\*\*line-weighted\*\*** metric and computes exactly what the docstring states (*\*"averaged over lines"\**). Therefore, this is **\*\*not an implementation bug\*\***.

However, line-weighted averaging gives equal weight to short and long sentences, diverging from **\*\*aggregate (word-weighted) corpus fertility\*\*** ($\sum \text{tokens} / \sum \text{words}$). When sentence lengths vary, short outlier sentences disproportionately distort the line-weighted average away from true corpus-wide token cost.

**## Why I Thought This**

In ratio analysis, the unweighted average of ratios $\frac{1}{N}\sum \frac{y\_i}{x\_i}$ does not equal the ratio of aggregates $\frac{\sum y\_i}{\sum x\_i}$. If a dataset contains short, fragmented sentences (e.g., titles, prompts, greetings), each short sentence gets a weight of $1/N$, exerting excessive leverage over the reported fertility. For LLM capacity planning and API billing, cost scales strictly with aggregate tokens per word.

**## Experiment**

Script: \`madayanthikaa/partA/audit/conceptual\_fertility.py\`

Command:

\`\`\`bash

python madayanthikaa/partA/audit/conceptual\_fertility.py

\`\`\`

Output logged to: \`madayanthikaa/partA/results/a2\_aggregation.txt\`

**## Result 1: Controlled 2-Line Extreme Test**

\- **\*\*Line 1\*\***: 2 words, 10 tokens $\implies f\_1 = 10 / 2 = 5.0$ tok/word

\- **\*\*Line 2\*\***: 100 words, 100 tokens $\implies f\_2 = 100 / 100 = 1.0$ tok/word

\- **\*\*Line-Weighted Mean (fertility.py)\*\***:

  $$(5.0 + 1.0) / 2 = \mathbf{3.000000\text{ tok/word}}$$

\- **\*\*Aggregate Corpus Fertility\*\***:

  $$(10 + 100) / (2 + 100) = 110 / 102 = \mathbf{1.078431\text{ tok/word}}$$

\- **\*\*Delta (Aggregate - Line-level)\*\***:

  $$1.078431 - 3.000000 = \mathbf{-1.921569\text{ tok/word}}\quad (-64.1\\%)$$

\- **\*\*Weighting Comparison\*\***:

  - Line-level mean: Line 1 = **\*\*50.00%\*\***, Line 2 = **\*\*50.00%\*\***

  - Aggregate corpus: Line 1 = **\*\*1.96%\*\*** of words, Line 2 = **\*\*98.04%\*\*** of words

**## Result 2: Starter Corpora Test (\`gpt2\` baseline)**

\- **\*\*English (\`eng\_sample.txt\`)\*\***:

  - 10 lines, 99 tokens, 79 words

  - Original line-level mean: **\*\*1.265206\*\*** tok/word

  - Aggregate corpus fertility: **\*\*1.253165\*\*** tok/word

  - Delta: **\*\*-0.012041\*\*** tok/word (-0.95%)

\- **\*\*Hindi (\`hin\_sample.txt\`)\*\***:

  - 10 lines, 459 tokens, 62 words

  - Original line-level mean: **\*\*7.448452\*\*** tok/word

  - Aggregate corpus fertility: **\*\*7.403226\*\*** tok/word

  - Delta: **\*\*-0.045227\*\*** tok/word (-0.61%)

**## Interpretation & Why This Proves the Claim**

The controlled test proves mathematically that line-weighted averaging can distort reported fertility by over 64% when sentence lengths vary. On the starter corpora, the delta is modest (\~1%) because sample lines are relatively uniform in length. However, in production workloads containing mixture of short queries and long documents, line-weighted metrics distort capacity planning models.

**## Conclusion**

Confirmed: **\*\*Conceptual / Metric-Definition Distinction (NOT an implementation bug)\*\***.

The original code correctly calculates what it documents ("averaged over lines"). For corpus-level token budgeting and serving capacity, aggregate word-weighted fertility must be used as the primary metric.

**---**

**# Experiment 3: Preprocessing Asymmetry (\`line.lower()\`)**

**## Hypothesis**

\`line = line.lower()\` in \`fertility.py\` is an identity no-op on Indic scripts (Devanagari, Tamil, Kannada) because these scripts have no uppercase/lowercase distinction. On Latin text, it forces lowercase, which alters GPT-2 tokenization.

**## Why I Thought This**

Unicode casing tables only define case mappings for scripts that have bicameral alphabets (Latin, Greek, Cyrillic). Brahmic scripts are unicameral.

**## Experiment**

Tested in \`madayanthikaa/partA/audit/isolate\_bugs.py\`.

**## Result**

\- **\*\*Hindi with \`lower()\`\*\***: 7.4485 tok/word

\- **\*\*Hindi without \`lower()\`\*\***: 7.4485 tok/word

  - **\*\*Delta\*\***: 0.0000 (Exact 0% difference)

\- **\*\*English with \`lower()\`\*\***: 1.2652 tok/word

\- **\*\*English without \`lower()\`\*\***: 1.2293 tok/word

  - **\*\*Delta\*\***: -0.0359 tok/word (-2.84%)

**## Interpretation**

The experiment conclusively proves that \`line.lower()\` has zero effect on Hindi, but introduces an artificial shift on English tokenization. This creates an asymmetric preprocessing condition across languages.

**## Conclusion**

Confirmed: **\*\*Harmless on Indic scripts, but an Asymmetric Preprocessing Distortive Factor for Latin scripts\*\***.

**---**

**# Experiment 4: Inert Dead Code (\`random.seed(1337)\`)**

**## Hypothesis**

\`random.seed(1337)\` at line 25 of \`fertility.py\` suggests stochastic processing, but \`random\` is never called anywhere else in the script. The script is entirely deterministic.

**## Why I Thought This**

A grep search for \`random\` in \`fertility.py\` only shows lines 21 (\`import random\`) and 25 (\`random.seed(1337)\`).

**## Experiment**

Remove \`import random\` and \`random.seed(1337)\`. Execution outputs are bit-for-bit identical.

**## Conclusion**

Confirmed: **\*\*Harmless / Inert Dead Code\*\***. Does not affect results, but creates false impression of stochasticity.

**---**

**# Experiment 5: Multilingual Evaluation Corpus Construction (FLORES-200)**

**## Hypothesis**

The starter corpora in \`starter\_kit/corpus\_sample/\` are 10-line toys that are not row-aligned (non-parallel) and lack Dravidian languages. A rigorous evaluation requires a standardized parallel benchmark (FLORES-200) across English (\`eng\_Latn\`), Hindi (\`hin\_Deva\`), Tamil (\`tam\_Taml\`), and Kannada (\`kan\_Knda\`).

**## Why I Thought This**

Comparing languages requires holding semantic information constant. Without parallel sentences, observed tokenization differences could stem from differing sentence semantics rather than tokenizer behavior.

**## Experiment**

Script: \`madayanthikaa/partA/prepare\_corpus.py\`

Command:

\`\`\`bash

python madayanthikaa/partA/prepare\_corpus.py

\`\`\`

**## Result**

\- **\*\*Archive\*\***: Downloaded \`flores200\_dataset.tar.gz\` (25,585,843 bytes) from Meta AI repository.

\- **\*\*Sentences\*\***: Exactly 1,012 parallel sentences extracted per language from the \`devtest\` split.

\- **\*\*Corpus Summary Statistics\*\***:

  - \`eng\`: 1,012 sents | 21,901 words | 131,966 codepoints | 132,096 UTF-8 bytes

  - \`hin\`: 1,012 sents | 25,643 words | 131,180 codepoints | 337,439 UTF-8 bytes

  - \`tam\`: 1,012 sents | 16,775 words | 154,131 codepoints | 421,635 UTF-8 bytes

  - \`kan\`: 1,012 sents | 16,100 words | 138,027 codepoints | 375,341 UTF-8 bytes

**## Interpretation**

Tamil and Kannada have significantly fewer whitespace words (16,775 and 16,100) than English (21,901) for the exact same semantic content, due to agglutinative morphology. This proves why \`tokens/word\` creates an unfair, distorted penalty for Dravidian languages.

**## Conclusion**

A1 Corpus constructed and verified. Exact 1,012 row alignment and NFC normalization established.

**---**

**# Experiment 6: Multi-Tokenizer, Multi-Denominator Benchmark on FLORES Corpus**

**## Hypothesis**

\`REPORT\_v0\` claimed that high token fertility in Hindi is an inescapable property of the script. We hypothesize that high fertility is primarily an artifact of English-centric vocabulary training (e.g. GPT-2), and that an Indic-specialized vocabulary (\`IndicBERTv2\`) will drastically reduce the token expansion ratio.

**## Why I Thought This**

GPT-2 was trained predominantly on English WebText with a 50k vocabulary, forcing it to fall back to byte-level fallback for non-Latin scripts. An Indic-specialized tokenizer with dedicated Devanagari and Dravidian subwords should represent full words and morphemes with far fewer tokens.

**## Experiment**

Script: \`madayanthikaa/partA/corrected\_analysis.py\`

Command:

\`\`\`bash

python madayanthikaa/partA/corrected\_analysis.py

\`\`\`

**## Result**

\- **\*\*Under \`gpt2\` (Tokens per Parallel Sentence)\*\***:

  - English: 26.7 (1.00x)

  - Hindi: 198.3 (**\*\*7.42x\*\***)

  - Tamil: 415.2 (**\*\*15.54x\*\***)

  - Kannada: 363.0 (**\*\*13.59x\*\***)

\- **\*\*Under \`IndicBERTv2\` (Tokens per Parallel Sentence)\*\***:

  - English: 26.8 (1.00x)

  - Hindi: 31.3 (**\*\*1.17x\*\***)

  - Tamil: 28.1 (**\*\*1.05x\*\***)

  - Kannada: 29.4 (**\*\*1.10x\*\***)

\- **\*\*Under \`Qwen2.5\` (Tokens per Parallel Sentence)\*\***:

  - English: 27.3 (1.00x)

  - Hindi: 120.5 (**\*\*4.42x\*\***)

  - Tamil: 166.8 (**\*\*6.11x\*\***)

  - Kannada: 188.9 (**\*\*6.92x\*\***)

**## Interpretation & Why This Proves the Claim**

Under \`IndicBERTv2\`, the Hindi-to-English ratio collapses from 7.42x down to 1.17x, and Tamil collapses from 15.54x down to 1.05x. Under \`Qwen2.5\`, it reaches 4.42x for Hindi and 6.11x for Tamil. This demonstrates that tokenizer choice strongly affects Indic token inflation. Indic-aware and multilingual tokenizers substantially reduce the token inflation observed with GPT-2. The experiment therefore does not support treating the observed inflation as simply an inherent property of the script.

Furthermore, the experiment does not support using the GPT-2 fertility ratio alone to claim that Hindi serving costs approximately 6× more per request. Fertility measures tokenizer expansion relative to a denominator; it is not itself a request-level serving-cost measurement.

**## Decision: Routing / Cost Metric & Model Recommendation**

\- **\*\*Benchmark Metric\*\***: For this controlled multilingual benchmark, the primary comparison metric is aggregate model tokens per aligned parallel sentence because the A1 corpus contains parallel sentences representing approximately the same underlying content across languages.

  - Diagnostics: tokens/whitespace word (linguistic/tokenization), tokens/grapheme (script/orthographic), tokens/byte (encoding-level), tokens/codepoint (Unicode normalization). None of these should automatically be treated as direct serving cost.

\- **\*\*Production Metric\*\***: For production capacity and cost monitoring, the primary metric should be input tokens per request, segmented by language and route, because actual model token count is what directly enters the inference workload.

\- **\*\*Model Recommendation\*\***: IndicBERTv2 demonstrates how Indic-specialized tokenization can reduce fragmentation, while Qwen2.5 provides a more relevant comparison because it is a generative multilingual model. Tokenizer/model-family choice materially affects Indic token counts, so routing and capacity planning should use measured token counts for the actual production model rather than extrapolating from GPT-2.

\- **\*\*Limitation\*\***: The A1 corpus is formal parallel text and may not represent casual conversational Indic traffic, including code-mixing and Romanized Indic text. Production token distributions should therefore be measured separately.

**---**

**# Experiment 7: KV Cache Exact Arithmetic and Decimal/Binary Disambiguation (B1)**

**## Hypothesis**

The serving engine's maximum concurrent sequence capacity can be derived purely from \`model\_spec.md\`. The benchmark log (\`bench\_log.csv\`) will disambiguate whether the engine operates under decimal GB ($10^9$) or binary GiB ($2^{30}$) memory accounting.

**## Why I Thought This**

GPU VRAM is 24 GB, but software frameworks define memory pools using either decimal gigabytes or binary gibibytes. Testing both against actual benchmark utilization will reveal the ground truth.

**## Experiment**

Script: \`madayanthikaa/partB/scripts/capacity\_audit.py\`

Command:

\`\`\`bash

python madayanthikaa/partB/scripts/capacity\_audit.py

\`\`\`

**## Result**

\- **\*\*Exact KV Bytes per Token [DERIVED]\*\***:

  $$2 \times 28 \times 8 \times 128 \times 2 = 114,688\text{ bytes} = 112.0\text{ KiB} \quad \text{[DERIVED]}$$

\- **\*\*Decimal Accounting ($10^9$) [DERIVED]\*\***:

  Available KV pool = $12.08\text{ GB} \implies 105,329.2\text{ tokens} \implies \mathbf{25.72\text{ sequences}}$ (Floor: 25 complete 4096-token sequences) \`[DERIVED]\`.

\- **\*\*Binary Accounting ($2^{30}$) [DERIVED]\*\***:

  Available KV pool = $12.77\text{ GiB} \implies 119,526.2\text{ tokens} \implies \mathbf{29.18\text{ sequences}}$ (Floor: 29 complete 4096-token sequences) \`[DERIVED]\`.

\- **\*\*Benchmark Disambiguation [MEASURED]\*\***:

  At batch 24 in \`bench\_log.csv\`, \`kv\_cache\_util\` is reported as **\*\*0.93\*\*** \`[MEASURED]\`.

  $$24 / 0.93 = \mathbf{25.8\text{ sequences}} \quad \text{[DERIVED]}$$

  This matches the decimal prediction ($25.72$) with 99.7% precision. Furthermore, batch 32 preempts exactly 7 sequences ($32 - 25 = 7$), and batch 48 preempts exactly 23 sequences ($48 - 25 = 23$) \`[MEASURED]\`.

**## Conclusion & Nuance (B1)**

The serving stack uses decimal GB accounting. Under the stated memory budget and static 4096-token allocation, the theoretical capacity estimate is **\*\*25 complete sequences\*\***.

*\*(Important: 25 is a theoretical capacity estimate under the stated static full-length allocation assumptions, not an absolute serving limit; dynamic paged allocators achieve higher sequence concurrency with variable-length or shorter prompts).\**

**---**

**# Experiment 8: Long-Context Scaling Anomaly (B2) & Reverse-Engineering \`reported\_tok\_s\` (B3)**

**## B2 Scaling Anomaly & Mechanism**

\- **\*\*Measured Data\*\***:

  - Batch 24: 1607.4 tok/s, 61.16s, kv\_cache\_util 0.93, 0 preempted sequences \`[MEASURED]\`

  - Batch 32: 1384.0 tok/s, 94.71s, kv\_cache\_util 0.97, 7 preempted sequences \`[MEASURED]\`

  - Batch 48: 1298.5 tok/s, 151.41s, kv\_cache\_util 0.97, 23 preempted sequences \`[MEASURED]\`

\- **\*\*Conclusion\*\***:

  > **\*\*"Increasing batch size beyond the KV-cache capacity causes preemption/recomputation pressure, so throughput no longer scales monotonically with batch size."\*\***

\- **\*\*Mechanism\*\***: When concurrency exceeds KV cache capacity, active sequences are evicted and must be recomputed upon resumption, creating pipeline bubbles and destroying useful throughput.

\- **\*\*Two-Wave Analytical Estimate\*\***: Processing 48 requests as two clean waves of 24 is estimated at $2 \times 61.16\text{s} = \mathbf{122.32\text{s}}$ \`[ESTIMATE]\`. *\*(Note: This is a simple two-wave estimate, not an observed benchmark measurement).\**

**## B3 Reverse-Engineering \`reported\_tok\_s\`**

\- **\*\*Misread Column\*\***: \`reported\_tok\_s\` was misread as generated-token throughput.

\- **\*\*Formula Proof [DERIVED]\*\***:

  $$\text{reported\\\_tok\\\_s} = \frac{\text{num\\\_requests} \times (\text{prompt\\\_len} + \text{gen\\\_len})}{\text{wall\\\_clock\\\_s}} \quad \text{[DERIVED]}$$

  - Row 1: $1 \times (512 + 256) / 10.94 = 70.20 \implies 70.2$ \`[DERIVED]\`

  - Row 6: $16 \times (512 + 256) / 13.91 = 883.39 \implies 883.2$ \`[DERIVED]\`

  - Row 11: $16 \times (3584 + 512) / 49.97 = 1311.51 \implies 1311.4$ \`[DERIVED]\`

  - Row 12: $24 \times (3584 + 512) / 61.16 = 1607.33 \implies 1607.4$ \`[DERIVED]\`

\- **\*\*Why it Disproves REPORT\_v0\*\***:

  \`reported\_tok\_s\` includes prompt tokens processed in parallel prefill. In reality, generated-token rate was 44% lower for long prompts:

  - Short prompt (batch 16, 512/256): $(16 \times 256) / 13.91\text{s} = \mathbf{294.5\text{ gen tok/s}}$ \`[DERIVED]\`

  - Long prompt (batch 16, 3584/512): $(16 \times 512) / 49.97\text{s} = \mathbf{163.9\text{ gen tok/s}}$ \`[DERIVED]\`

  Therefore, the long-prompt case does NOT demonstrate better generation throughput.

**## Generated Output Rates for Batch 24 (Long Prompt)**

\- **\*\*Metric 1: End-to-End Generated-Token Rate\*\***:

  $$\frac{24 \times 512}{61.16\text{s}} = \mathbf{200.92\text{ gen tok/s}} \quad \text{[DERIVED]}$$

\- **\*\*Metric 2: Steady-State Decode Rate Inferred from ITL\*\***:

  $$\frac{24}{0.09607\text{s}} = \mathbf{249.82\text{ gen tok/s}} \quad \text{[DERIVED]}$$

*\*(Note: These measure different quantities and are not interchangeable. Metric 1 amortizes prefill and tail latency across wall clock; Metric 2 measures pure instantaneous decode).\**

**---**

**# B4 Production Telemetry Recommendation**

\> **\*\*"Production should monitor the serving engine's KV-cache preemption/recomputation counter. If the production stack is vLLM, \`num\_preemptions\_total\` is an appropriate concrete counter; otherwise use the equivalent counter exposed by the actual serving engine."\*\***  

\> Its purpose is to detect when increasing concurrency causes KV-cache pressure and preemption/recomputation.