# Part A3: Corrected Multilingual Tokenizer Analysis

## Executive Summary
We evaluated three tokenizers across four languages on the 1,012 parallel sentences of the FLORES-200 `devtest` benchmark:
- **Languages**: English (`eng_Latn`), Hindi (`hin_Deva`), Tamil (`tam_Taml`), and Kannada (`kan_Knda`).
- **Tokenizers**:
  1. `gpt2` (tiktoken BPE, vocab: 50,257 -- English-centric baseline)
  2. `IndicBERTv2` (`ai4bharat/IndicBERTv2-MLM-only`, vocab: 250,000 -- Indic-specialized)
  3. `Qwen2.5` (`Qwen/Qwen2.5-0.5B`, vocab: 151,643 -- modern multilingual foundation model)
- **Denominators Analyzed**: Parallel Sentence, Whitespace Word, Extended Grapheme Cluster (UAX #29), UTF-8 Byte, and Unicode Codepoint.

---

## 1. Measured Results Table

| Tokenizer | Language | Total Tokens | Tok / Sentence | Tok / Word | Tok / Grapheme | Tok / Byte | Tok / Codepoint |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`gpt2`** | **eng** | 27,044 | 26.7 | 1.24 | 0.20 | 0.205 | 0.205 |
| | **hin** | 200,688 | 198.3 | 7.83 | 2.33 | 0.595 | 1.530 |
| | **tam** | 420,171 | 415.2 | 25.05 | 4.21 | 0.997 | 2.726 |
| | **kan** | 367,366 | 363.0 | 22.82 | 4.07 | 0.979 | 2.662 |
| **`IndicBERTv2`** | **eng** | 27,078 | 26.8 | 1.24 | 0.20 | 0.205 | 0.205 |
| | **hin** | 31,661 | 31.3 | 1.24 | 0.37 | 0.094 | 0.241 |
| | **tam** | 28,439 | 28.1 | 1.70 | 0.28 | 0.067 | 0.185 |
| | **kan** | 29,715 | 29.4 | 1.85 | 0.33 | 0.079 | 0.215 |
| **`Qwen2.5`** | **eng** | 27,621 | 27.3 | 1.26 | 0.21 | 0.209 | 0.209 |
| | **hin** | 121,957 | 120.5 | 4.76 | 1.42 | 0.361 | 0.930 |
| | **tam** | 168,828 | 166.8 | 10.06 | 1.69 | 0.400 | 1.095 |
| | **kan** | 191,127 | 188.9 | 11.87 | 2.12 | 0.509 | 1.385 |

---

## 2. Cross-Lingual Ratios Relative to English (English = 1.00x)

| Tokenizer | Language | x Tokens / Sentence | x Tokens / Word | x Tokens / Grapheme | x Tokens / Byte |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **`gpt2`** | **hin** | **7.42x** | 6.34x | 11.39x | 2.90x |
| | **tam** | **15.54x** | 20.28x | 20.55x | 4.86x |
| | **kan** | **13.59x** | 18.48x | 19.83x | 4.78x |
| **`IndicBERTv2`** | **hin** | **1.17x** | 1.00x | 1.80x | 0.46x |
| | **tam** | **1.05x** | 1.37x | 1.39x | 0.33x |
| | **kan** | **1.10x** | 1.49x | 1.60x | 0.39x |
| **`Qwen2.5`** | **hin** | **4.42x** | 3.77x | 6.79x | 1.73x |
| | **tam** | **6.11x** | 7.98x | 8.10x | 1.91x |
| | **kan** | **6.92x** | 9.41x | 10.12x | 2.44x |

---

## 3. What Does Each Denominator Hold Constant?

1. **Tokens / Whitespace Word**:
   - *Holds constant*: The number of whitespace delimiters in text.
   - *Why it fails across languages*: Highly agglutinative languages like Tamil and Kannada combine multiple morphemes, case markers, and postpositions into single compound words. English requires 21,901 words to express what Tamil expresses in 16,775 words and Kannada in 16,100 words. Dividing by words penalizes Dravidian languages with an artificially small denominator.
2. **Tokens / UTF-8 Byte**:
   - *Holds constant*: Raw binary storage size.
   - *Why it fails across languages*: UTF-8 encodes ASCII (English) using 1 byte per character, but encodes Devanagari and Dravidian scripts using 3 bytes per character. Thus, the byte denominator gives an unfair 3x numerical advantage to Indic scripts, masking severe token fragmentation.
3. **Tokens / Extended Grapheme Cluster (UAX #29)**:
   - *Holds constant*: Visually perceived typographical characters (base consonant + matra + virama combinations).
   - *Utility*: Far better than Python `len()` (which counts raw Unicode codepoints), but typographical density still varies across scripts.
4. **Tokens / Parallel Sentence**:
   - *Holds constant*: **Semantic Information Content**.
   - *Why it is the gold standard*: A translated parallel sentence conveys identical semantic meaning across all four languages. Because LLM context windows and user interactions are fundamentally informational, comparing tokens per parallel sentence is the only denominator that isolates tokenization efficiency without orthographic bias.

---

## 4. Evaluation of REPORT_v0 Claims

`REPORT_v0.md` asserted:
> *"Root cause: Hindi simply has more Unicode characters per word, so any tokenizer will struggle. This is a property of the script, not the tokenizer."*
> *"Hindi fertility is 5.89x worse than English. Serving Hindi will cost us roughly 6x more per request than English."*

**Our empirical measurements refute both assertions**:
1. **Script vs. Tokenizer Choice**:
   - Under `gpt2`, Hindi requires **7.42x** more tokens per sentence than English, and Tamil requires **15.54x**.
   - However, under `IndicBERTv2`, the cross-lingual expansion relative to English drops to **1.17x for Hindi**, **1.05x for Tamil**, and **1.10x for Kannada**.
   - Under `Qwen2.5`, Hindi requires **4.42x**, Tamil **6.11x**, and Kannada **6.92x**.
   - **Conclusion**: Tokenizer choice strongly affects Indic token inflation. Indic-aware and multilingual tokenizers substantially reduce the token inflation observed with GPT-2. The experiment therefore does not support treating the observed inflation as simply an inherent property of the script.
2. **Fertility vs. Request Serving Cost**:
   - The experiment does not support using the GPT-2 fertility ratio alone to claim that Hindi serving costs approximately 6× more per request. Fertility measures tokenizer expansion relative to a denominator; it is not itself a request-level serving-cost measurement.
   - Conflating prompt tokens with request serving cost ignores the asymmetry between compute-bound parallel prefill and memory-bandwidth-bound autoregressive decode.

---

## 5. A3 Decision: Routing / Cost Metric

For this controlled multilingual benchmark, the primary comparison metric is aggregate model tokens per aligned parallel sentence because the A1 corpus contains parallel sentences representing approximately the same underlying content across languages.

### Diagnostic Denominators Breakdown:
- **tokens / whitespace word**: useful linguistic/tokenization diagnostic (reveals subword splits per whitespace token, but heavily distorted by agglutinative morphology in Dravidian languages where words fuse grammatical morphemes).
- **tokens / grapheme**: useful script/orthographic normalization diagnostic (measures subword fragmentation against visually perceived typographical characters under UAX #29).
- **tokens / byte**: useful encoding-level diagnostic (evaluates tokenization density relative to raw UTF-8 byte representation, though 3-byte Indic UTF-8 offsets direct comparability).
- **tokens / codepoint**: useful Unicode normalization diagnostic (evaluates fragmentation across Unicode scalar values, highlighting decomposition artifacts).
- **None of these should automatically be treated as direct serving cost.**

### Production Metric Distinction:
For production capacity and cost monitoring, the primary metric should be **input tokens per request, segmented by language and route**, because actual model token count is what directly enters the inference workload.

---

## 6. Model Recommendation & Routing Strategy

- **Architectural Role of Evaluated Models**:
  - `IndicBERTv2` demonstrates how Indic-specialized tokenization can reduce fragmentation, while `Qwen2.5` provides a more relevant comparison because it is a generative multilingual model.
- **Strategic Recommendation**:
  - Tokenizer/model-family choice materially affects Indic token counts, so routing and capacity planning should use measured token counts for the actual production model rather than extrapolating from GPT-2.

---

## 7. Limitations & Caveats

- **Benchmark Domain & Register**:
  The A1 corpus is formal parallel text and may not represent casual conversational Indic traffic, including code-mixing and Romanized Indic text. Production token distributions should therefore be measured separately.
