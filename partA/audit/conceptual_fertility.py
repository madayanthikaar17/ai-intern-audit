#!/usr/bin/env python3
"""
partA/audit/conceptual_fertility.py

Conceptual/Metric-Definition Experiment for fertility.py:
Demonstrates the difference between Line-Weighted Fertility (mean of per-line ratios)
and Aggregate Corpus Fertility (total tokens / total words).

Context:
  Original fertility.py computes:
      mean(tokens_i / words_i) across lines.
  This is mathematically valid and matches the docstring ("averaged over lines").
  However, it produces a LINE-WEIGHTED metric, which treats each line equally
  regardless of length. For corpus-level token efficiency, aggregate tokens / aggregate
  words (WORD-WEIGHTED) is the more appropriate metric.
"""

import sys
from pathlib import Path
import unicodedata
import tiktoken

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_controlled_example():
    """
    Controlled 2-line experiment illustrating the line-weighted vs word-weighted divergence.
    Line 1: 2 words, 10 tokens (fertility = 5.0)
    Line 2: 100 words, 100 tokens (fertility = 1.0)
    """
    line1_words, line1_tokens = 2, 10
    line2_words, line2_tokens = 100, 100

    f1 = line1_tokens / line1_words  # 5.0
    f2 = line2_tokens / line2_words  # 1.0

    # Line-weighted mean (fertility.py approach)
    line_mean = (f1 + f2) / 2.0  # 3.0

    # Aggregate corpus-level fertility (total tokens / total words)
    total_tokens = line1_tokens + line2_tokens  # 110
    total_words = line1_words + line2_words    # 102
    agg_fertility = total_tokens / total_words  # 1.078431...

    delta = agg_fertility - line_mean  # -1.921569...

    # Weighting breakdown
    w_line1_line = 0.5 * 100.0
    w_line2_line = 0.5 * 100.0

    w_line1_word = (line1_words / total_words) * 100.0
    w_line2_word = (line2_words / total_words) * 100.0

    return {
        "line1": (line1_words, line1_tokens, f1),
        "line2": (line2_words, line2_tokens, f2),
        "line_mean": line_mean,
        "agg_fertility": agg_fertility,
        "delta": delta,
        "weights": (w_line1_line, w_line2_line, w_line1_word, w_line2_word),
    }


def analyze_starter_corpus(corpus_path: Path, enc):
    """
    Computes line-weighted mean fertility and aggregate fertility on a corpus file
    using the exact baseline tokenization and whitespace splitting of fertility.py.
    """
    lines = []
    with open(corpus_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)

    per_line_fertility = []
    total_tokens = 0
    total_words = 0

    for line in lines:
        line_lower = line.lower()
        toks = enc.encode(line_lower)
        words = line_lower.split(" ")  # preserving original fertility.py behavior
        num_toks = len(toks)
        num_words = len(words)

        total_tokens += num_toks
        total_words += num_words
        per_line_fertility.append(num_toks / num_words)

    n_lines = len(per_line_fertility)
    line_mean = sum(per_line_fertility) / n_lines
    agg_fertility = total_tokens / total_words
    delta = agg_fertility - line_mean

    return {
        "lines": n_lines,
        "tokens": total_tokens,
        "words": total_words,
        "line_mean": line_mean,
        "agg_fertility": agg_fertility,
        "delta": delta,
    }


def find_starter_path(filename: str) -> Path:
    """Find sample corpus file across common relative paths."""
    candidates = [
        Path("starter_kit/corpus_sample") / filename,
        Path("../starter_kit/corpus_sample") / filename,
        Path("../../starter_kit/corpus_sample") / filename,
        Path("corpus_sample") / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def main():
    print("=" * 80)
    print("A2 CONCEPTUAL EXPERIMENT: LINE-WEIGHTED VS AGGREGATE CORPUS FERTILITY")
    print("=" * 80)

    # 1. Controlled Example
    res = run_controlled_example()
    print("\n--- Part 1: Controlled 2-Line Example ---")
    print("Line 1:  2 words,  10 tokens -> fertility = {:.1f}".format(res["line1"][2]))
    print("Line 2: 100 words, 100 tokens -> fertility = {:.1f}".format(res["line2"][2]))
    print()
    print("Original line-level mean (line-weighted):")
    print("  ({:.1f} + {:.1f}) / 2 = {:.6f}".format(res["line1"][2], res["line2"][2], res["line_mean"]))
    print("Aggregate corpus fertility (word-weighted):")
    print("  ({} + {}) / ({} + {}) = {} / {} = {:.6f}".format(
        res["line1"][1], res["line2"][1], res["line1"][0], res["line2"][0],
        res["line1"][1] + res["line2"][1], res["line1"][0] + res["line2"][0],
        res["agg_fertility"]
    ))
    print("Delta (Aggregate - Line-level):")
    print("  {:.6f} - {:.6f} = {:.6f}".format(res["agg_fertility"], res["line_mean"], res["delta"]))
    print()
    print("Weighting comparison:")
    print("  Line-level mean : Line 1 = {:.2f}%, Line 2 = {:.2f}%".format(res["weights"][0], res["weights"][1]))
    print("  Aggregate corpus: Line 1 = {:.2f}% of words, Line 2 = {:.2f}% of words".format(res["weights"][2], res["weights"][3]))

    # 2. Starter Corpus
    print("\n--- Part 2: Starter Corpora (gpt2 tokenizer) ---")
    enc = tiktoken.get_encoding("gpt2")

    eng_path = find_starter_path("eng_sample.txt")
    hin_path = find_starter_path("hin_sample.txt")

    if eng_path.exists() and hin_path.exists():
        eng_res = analyze_starter_corpus(eng_path, enc)
        hin_res = analyze_starter_corpus(hin_path, enc)

        print(f"English ({eng_path}):")
        print(f"  - lines: {eng_res['lines']}")
        print(f"  - tokens: {eng_res['tokens']}")
        print(f"  - words: {eng_res['words']}")
        print(f"  - original line-level fertility = {eng_res['line_mean']:.6f}")
        print(f"  - aggregate fertility = {eng_res['agg_fertility']:.6f}")
        print(f"  - delta = {eng_res['delta']:.6f}")
        print()
        print(f"Hindi ({hin_path}):")
        print(f"  - lines: {hin_res['lines']}")
        print(f"  - tokens: {hin_res['tokens']}")
        print(f"  - words: {hin_res['words']}")
        print(f"  - original line-level fertility = {hin_res['line_mean']:.6f}")
        print(f"  - aggregate fertility = {hin_res['agg_fertility']:.6f}")
        print(f"  - delta = {hin_res['delta']:.6f}")
    else:
        print("Starter corpora not found at expected paths.")

    print("\n" + "=" * 80)
    print("Summary of Conceptual Finding:")
    print("The original fertility.py calculates: mean(tokens_i / words_i) across lines.")
    print("This is mathematically valid and computes exactly what the script docstring states.")
    print("It is NOT an implementation bug. It is a conceptual metric distinction:")
    print("  - Line-weighted mean answers: 'What is the average fertility of a sentence?'")
    print("  - Aggregate fertility answers: 'What is the total token cost per word across the corpus?'")
    print("When sentences have unequal lengths, short outlier sentences exert disproportionate")
    print("influence on the line-weighted mean, shifting it away from the true corpus-wide cost.")
    print("=" * 80)


if __name__ == "__main__":
    main()
