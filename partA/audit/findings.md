# Part A2: Audit of `fertility.py` and Associated Metrics

This audit applies the strict evidence rule to investigate code bugs, conceptual/metric flaws, and harmless artifacts in `fertility.py`.

---

## Finding 1: Code Bug -- Fragile Whitespace Splitting (`words = line.split(" ")`)

- **Classification**: **Real Code Bug**
- **Hypothesis**: Splitting strings on an explicit space character (`line.split(" ")`) instead of default whitespace (`line.split()`) fails to collapse consecutive spaces or handle tabs, producing empty strings `""` as items in the `words` list. This inflates the denominator (`len(words)`), thereby artificially deflating the reported fertility.
- **Evidence from Corpus**:
  - `eng_sample.txt` line 7: `"Please keep the books  in the cupboard."` contains two consecutive spaces between `"books"` and `"in"`.
  - `hin_sample.txt` line 10: `"किताबें  अलमारी में रखी हैं।"` contains two consecutive spaces between `"किताबें"` and `"अलमारी"`.
- **Experiment**:
  - Run `isolate_bugs.py` comparing `line.split(" ")` vs `line.split()` on the unmodified baseline corpus using `gpt2`.
- **Before (`split(" ")`)**:
  - English fertility: **1.2652** tok/word (reported rounded as 1.27)
  - Hindi fertility: **7.4485** tok/word (reported rounded as 7.45)
  - Cross-language ratio: **5.8871x** (reported rounded as 5.89x)
- **After (`split()`)**:
  - English fertility: **1.2831** tok/word
  - Hindi fertility: **7.5985** tok/word
  - Cross-language ratio: **5.9221x**
- **Numerical Delta**:
  - English: **+0.0179** tok/word (+1.41%)
  - Hindi: **+0.1500** tok/word (+2.01%)
  - Ratio: **+0.0350x**
- **Why the Delta Proves the Claim**:
  In `split(" ")`, the double spaces generated an extra empty string element in `words`, making `len(words)` equal to 8 instead of 7 for English line 7, and 6 instead of 5 for Hindi line 10. Replacing it with `split()` removed the empty strings, strictly reducing the denominator and increasing true tokens-per-word.
- **Revised Conclusion**:
  `words = line.split(" ")` is an unambiguous code bug and must be replaced with `words = line.split()`.

---

## Finding 2: Conceptual & Metric Flaw -- Conflating Tokens/Word Across Languages

- **Classification**: **Conceptual Problem (Computes what it says, but answers the wrong question)**
- **Hypothesis**: The code computes `len(tokens) / len(words)` correctly, but comparing this ratio directly between English and Hindi to claim "Hindi is 5.89x worse" is linguistically invalid. Words separated by whitespace do not represent comparable units of semantic or syntactic information across distinct language families.
- **Linguistic Reality**:
  - English uses isolating/analytic structures with many short function words ("in", "the", "to", "of").
  - Hindi and Dravidian languages are morphologically richer and feature postpositions, complex case inflection, and compound predicates where grammatical relations are fused or expressed in fewer whitespace tokens.
- **Evidence & Comparison with Other Denominators**:
  - Tokens / Whitespace Word: English = 1.2692, Hindi = 7.5246 $\implies$ **5.93x ratio**
  - Tokens / Unicode Codepoint: English = 0.2210, Hindi = 1.5828 $\implies$ **7.16x ratio**
  - Tokens / UTF-8 Byte: English = 0.2210, Hindi = 0.6008 $\implies$ **2.72x ratio**
- **Why this Proves the Claim**:
  The ratio of tokens between English and Hindi drops from **5.93x** under the word denominator to **2.72x** under the byte denominator! If word count held information constant, the ratio would be invariant. The fact that the ratio swings wildly across denominators proves that "word" is not an apples-to-apples basis of comparison.
- **Revised Conclusion**:
  Tokens per whitespace word cannot be used to compare cross-lingual efficiency or model capacity. Parallel sentence comparison or byte-normalized metrics are required to control for information content.

---

## Finding 3: Conceptual Flaw -- Conflating Tokenizer Fertility with Serving Cost

- **Classification**: **Business & Serving Fallacy in REPORT_v0**
- **Hypothesis**: `REPORT_v0` concludes: *"Hindi fertility is 5.89x worse than English. Serving Hindi will cost us roughly 6x more per request than English."* This assumes serving cost scales linearly 1:1 with prompt tokenization fertility. In reality, serving costs are dominated by batching, prefill vs. decode latency asymmetry, and memory bandwidth.
- **Technical Reality**:
  1. **Prefill vs. Decode**: Processing prompt tokens (prefill) is parallelized and compute-bound; generating new tokens (decode) is autoregressive and memory-bandwidth bound. A request with a 6x longer prompt only adds prefill time, which is typically a fraction of total request latency.
  2. **Batching Amortization**: Memory bandwidth costs of loading model weights are amortized across all requests in a batch.
- **Revised Conclusion**:
  A 5.89x increase in prompt tokens does not translate to 5.89x serving cost. Capacity planning based on this assumption will severely over-provision hardware.

---

## Finding 4: Conceptual Metric Issue -- Line-Weighted vs Aggregate (Word-Weighted) Fertility

- **Classification**: **Conceptual / Metric-Definition Distinction (NOT an implementation bug)**
- **Hypothesis**: The original `fertility.py` computes:
  $$\text{mean}\left(\frac{\text{tokens}_i}{\text{words}_i}\right) = \frac{1}{N} \sum_{i=1}^N \frac{\text{tokens}_i}{\text{words}_i}$$
  across lines. This is mathematically valid and computes exactly what the script docstring states (*"averaged over lines"*). It is therefore **not an implementation bug**. However, it produces a **line-weighted** metric where every line receives equal weight ($1/N$). In contrast, corpus-level token efficiency is an **aggregate (word-weighted)** metric:
  $$\text{Corpus Fertility} = \frac{\sum \text{tokens}_i}{\sum \text{words}_i} = \sum_{i=1}^N \left( \frac{\text{words}_i}{\sum \text{words}_j} \right) \left( \frac{\text{tokens}_i}{\text{words}_i} \right)$$
  When line lengths vary, short sentences with high fragmentation disproportionately distort the line-weighted average away from true corpus token costs.

- **Experiment 1: Controlled 2-Line Extreme Test**:
  - **Setup**:
    - Line 1: 2 words, 10 tokens $\implies f_1 = 10 / 2 = 5.0$ tok/word
    - Line 2: 100 words, 100 tokens $\implies f_2 = 100 / 100 = 1.0$ tok/word
  - **Results**:
    - Line-weighted mean (fertility.py): $(5.0 + 1.0) / 2 = \mathbf{3.000000}$ tok/word
    - Aggregate corpus fertility: $(10 + 100) / (2 + 100) = 110 / 102 = \mathbf{1.078431}$ tok/word
    - Delta (Aggregate - Line-level): $1.078431 - 3.000000 = \mathbf{-1.921569}$ tok/word (-64.1% shift!)
  - **Weighting Comparison**:
    - Line-weighted metric: Line 1 = **50.00%**, Line 2 = **50.00%**
    - Aggregate metric: Line 1 = **1.96%** of words, Line 2 = **98.04%** of words

- **Experiment 2: Starter Corpora Test (`gpt2` tokenizer, baseline whitespace split)**:
  - Script: `your-submission/partA/audit/conceptual_fertility.py` (logged in `partA/results/a2_aggregation.txt`)
  - **English (`eng_sample.txt`)**:
    - 10 lines, 99 tokens, 79 words
    - Original line-level mean: **1.265206** tok/word
    - Aggregate corpus fertility: **1.253165** tok/word
    - Delta: **-0.012041** tok/word (-0.95%)
  - **Hindi (`hin_sample.txt`)**:
    - 10 lines, 459 tokens, 62 words
    - Original line-level mean: **7.448452** tok/word
    - Aggregate corpus fertility: **7.403226** tok/word
    - Delta: **-0.045227** tok/word (-0.61%)

- **Why this Matters for Token Budgeting and Capacity Planning**:
  In production serving environments, GPU VRAM allocation, KV cache sizing, and API pricing depend strictly on the **total volume of tokens processed and generated** ($\sum \text{tokens}$), not the unweighted average of individual sentence ratios. If an application receives a heterogeneous mix of short queries (e.g. conversational greetings, fragmented queries) and long documents, a line-weighted metric will overstate the expected token burden if short queries fragment heavily, or understate it if long documents fragment heavily. Aggregate word-weighted fertility reflects the actual economic and memory cost per word of text processed.

- **Revised Conclusion**:
  Acknowledge that `fertility.py` implements its stated line-weighted definition correctly. However, for corpus-wide efficiency evaluation and serving capacity planning, adopt aggregate word-weighted fertility ($\sum \text{tokens} / \sum \text{words}$) as the primary standard, reporting line-level dispersion (mean and standard deviation) only as a secondary measure of sentence-level variance.

---

## Finding 5: Suspicious but Harmless/Asymmetric -- `line = line.lower()`

- **Classification**: **Harmless on Indic Scripts / Asymmetric Preprocessing on Latin**
- **Hypothesis**: `line.lower()` looks like standard preprocessing, but Devanagari and Dravidian scripts are unicameral (they have no upper/lower case). Thus, `lower()` is a complete no-op for Hindi, but alters Latin text.
- **Experiment**:
  - Run with and without `line.lower()`.
- **Measured Result**:
  - Hindi with `lower()`: **7.4485** | Hindi without `lower()`: **7.4485** (Delta: **0.0000**, 0.0%)
  - English with `lower()`: **1.2652** | English without `lower()`: **1.2293** (Delta: **-0.0359**, -2.84%)
- **Why this Proves the Claim**:
  Zero delta on Hindi proves it is completely harmless on Indic text, while the English delta confirms that lowercasing introduces script-specific distortion.
- **Revised Conclusion**:
  `line.lower()` should not be applied when evaluating true production tokenization unless the production pipeline strictly lowercases all user inputs.

---

## Finding 6: Suspicious but Inert -- `random.seed(1337)`

- **Classification**: **Harmless Dead Code**
- **Hypothesis**: `random.seed(1337)` suggests stochastic behavior or random subsampling, but `random` is never called in `fertility.py`.
- **Experiment**:
  - Grep for `random` across the file. Lines 21 and 25 are the only mentions.
  - Removing lines 21 and 25 yields identical deterministic outputs.
- **Revised Conclusion**:
  Vestigial dead code. Harmless to execution, but misleading to human auditors.

---

## Finding 7: Suspicious but Good Practice -- `unicodedata.normalize("NFC", line)`

- **Classification**: **Harmless and Essential Best Practice**
- **Hypothesis**: Applying NFC normalization might look like unnecessary data modification, but in multilingual text (especially Indic scripts), characters can be represented either as precomposed characters or decomposed base characters + combining diacritics. NFC standardizes text representation.
- **Revised Conclusion**:
  Retain NFC normalization. It prevents artificial subword fragmentation caused by inconsistent Unicode encoding from diverse data sources.
