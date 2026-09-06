# Submission Reproducibility Guide

## Environment & Dependencies
- **Python Version**: Python 3.10+ (tested on Python 3.11)
- **Required Libraries**:
  ```bash
  pip install -r requirements.txt
  ```
  Contents: `tiktoken>=0.7.0`, `transformers>=4.40.0`, `tokenizers>=0.19.0`, `regex>=2024.0.0`

---

## Directory Structure
```text
your-submission-final/
├── README.md                   # This reproduction guide
├── NOTEBOOK.md                 # Chronological lab notebook of all experiments
├── AI_USAGE.md                 # Transparent AI usage disclosure & independent verification
├── FINAL_AUDIT.md              # Quality control checklist against assignment rubric
├── DEFENSE_PREP.md             # 30-minute live defense guide with formulas & counterfactuals
├── FINAL_CHANGELOG.md          # Itemized audit and remediation changelog
├── requirements.txt            # Minimal Python dependencies
├── partA/
│   ├── prepare_corpus.py       # Script that extracted FLORES-200 1,012 parallel sentences
│   ├── corpus_stats.csv        # Summary word, codepoint, and byte statistics
│   ├── corrected_analysis.py   # Multi-tokenizer, multi-denominator benchmarking script
│   ├── memo.md                 # <=1 page leadership recommendation memo
│   ├── corpus/
│   │   ├── README.md           # Dataset provenance, alignment, and caveat documentation
│   │   ├── metadata.json       # Machine-readable corpus metadata
│   │   ├── eng.txt             # 1,012 English parallel sentences (NFC-normalized)
│   │   ├── hin.txt             # 1,012 Hindi parallel sentences
│   │   ├── tam.txt             # 1,012 Tamil parallel sentences
│   │   └── kan.txt             # 1,012 Kannada parallel sentences
│   ├── audit/
│   │   ├── isolate_bugs.py          # Script running minimal isolation experiments for A2
│   │   ├── conceptual_fertility.py  # Conceptual line-weighted vs aggregate word-weighted experiment
│   │   ├── audit_results.md         # Formal A2 audit write-up under strict evidence rule
│   │   └── findings.md              # Detailed findings report & metric comparison
│   └── results/
│       ├── a2_aggregation.txt               # Execution log of conceptual line-weighted vs aggregate test
│       ├── corrected_fertility.csv          # Raw token metrics across tokenizers & denominators
│       ├── cross_lingual_ratios.csv         # Cross-lingual expansion ratios relative to English
│       ├── sentence_distribution_stats.csv  # Mean, std dev, median, and IQR distribution stats
│       └── corrected_analysis.md            # Comprehensive A3 analysis & denominator justification
├── partB/
│   ├── calculations.md         # Nuanced B1 KV cache arithmetic & memory budgeting
│   ├── analysis.md             # In-depth B2 anomaly, B3 goodput rates, and B4 telemetry analysis
│   ├── scripts/
│   │   └── capacity_audit.py   # Reproducible script executing all Part B derivations
│   └── results/
│       └── capacity_summary.json # Machine-readable summary of capacity & goodput metrics
└── partC/
    ├── memo.md                 # <=1 page decision memo with labeled arithmetic & kill criteria
    └── evaluation_plan.md      # Multi-dimensional objective evaluation rubric & protocol
```

---

## Step-by-Step Reproduction Instructions

### 1. Reproduce Original Baseline
```bash
python starter_kit/fertility.py \
    --corpus eng=starter_kit/corpus_sample/eng_sample.txt \
    --corpus hin=starter_kit/corpus_sample/hin_sample.txt \
    --tokenizer gpt2
```
Expected output: English fertility = 1.27 tok/word, Hindi fertility = 7.45 tok/word (5.89× ratio).

### 2. Reproduce A2 Bug Isolation Experiments
```bash
python your-submission-final/partA/audit/isolate_bugs.py
```
Measures the `split(" ")` bug (+0.0179 eng, +0.1500 hin), casing (`lower()` zero delta on Hindi), and Unicode codepoints vs. grapheme clusters.

### 2b. Reproduce A2 Conceptual Metric Experiment (Line-Weighted vs. Aggregate)
```bash
python your-submission-final/partA/audit/conceptual_fertility.py
```
Demonstrates why `fertility.py`'s line-weighted mean (3.000000 on toy, 7.448452 on starter Hindi) diverges from aggregate word-weighted corpus fertility (1.078431 on toy, 7.403226 on starter Hindi), proving the conceptual metric distinction without claiming an implementation bug. (Logged in `partA/results/a2_aggregation.txt`).

### 3. Re-extract FLORES-200 Evaluation Corpus (A1)
```bash
python your-submission-final/partA/prepare_corpus.py
```
Extracts 1,012 parallel sentences from Meta AI's official FLORES-200 `devtest` split across English, Hindi, Tamil, and Kannada.

### 4. Reproduce Multi-Tokenizer Benchmark (A3)
```bash
python your-submission-final/partA/corrected_analysis.py
```
Evaluates `gpt2`, `ai4bharat/IndicBERTv2-MLM-only`, and `Qwen/Qwen2.5-0.5B` across all 4 languages and 5 denominators, outputting CSVs and distribution statistics.

### 5. Reproduce Capacity Reconciliation & Goodput Rates (Part B)
```bash
python your-submission-final/partB/scripts/capacity_audit.py
```
Verifies KV-cache memory (114,688 bytes/tok), concurrency (~25 sequences), reverse-engineers `reported_tok_s`, and computes both output generation rates (200.92 gen tok/s and 249.82 gen tok/s).
