#!/usr/bin/env python3
"""
isolate_bugs.py -- Minimal isolation experiments for A2 audit of fertility.py
Tests each candidate flaw/behavior in isolation against the verified baseline.
"""

import sys
import unicodedata
import tiktoken
from pathlib import Path

def load_data(path: str, normalize_nfc=True):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if normalize_nfc:
                line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines

def baseline_analyze(lines, encode):
    per_line_fertility = []
    per_line_tpc = []
    for line in lines:
        line_l = line.lower()
        tokens = encode(line_l)
        words = line_l.split(" ")
        chars = len(line_l)
        per_line_fertility.append(len(tokens) / len(words))
        per_line_tpc.append(len(tokens) / chars)
    n = len(per_line_fertility)
    return sum(per_line_fertility) / n, sum(per_line_tpc) / n

def experiment_split_clean(lines, encode):
    """Test replacing split(' ') with split()"""
    per_line_fertility = []
    per_line_tpc = []
    for line in lines:
        line_l = line.lower()
        tokens = encode(line_l)
        words = line_l.split()
        chars = len(line_l)
        per_line_fertility.append(len(tokens) / len(words))
        per_line_tpc.append(len(tokens) / chars)
    n = len(per_line_fertility)
    return sum(per_line_fertility) / n, sum(per_line_tpc) / n

def experiment_micro_average(lines, encode):
    """Test corpus-level micro-average (sum(tokens) / sum(words)) vs macro-average"""
    total_tokens = 0
    total_words_space = 0
    total_words_clean = 0
    total_chars = 0
    for line in lines:
        line_l = line.lower()
        tokens = encode(line_l)
        total_tokens += len(tokens)
        total_words_space += len(line_l.split(" "))
        total_words_clean += len(line_l.split())
        total_chars += len(line_l)
    
    micro_fert_space = total_tokens / total_words_space
    micro_fert_clean = total_tokens / total_words_clean
    micro_tpc = total_tokens / total_chars
    return micro_fert_space, micro_fert_clean, micro_tpc

def experiment_casing(lines, encode):
    """Test removing line.lower()"""
    per_line_fertility = []
    per_line_tpc = []
    for line in lines:
        tokens = encode(line)
        words = line.split(" ")
        chars = len(line)
        per_line_fertility.append(len(tokens) / len(words))
        per_line_tpc.append(len(tokens) / chars)
    n = len(per_line_fertility)
    return sum(per_line_fertility) / n, sum(per_line_tpc) / n

def main():
    enc = tiktoken.get_encoding("gpt2")
    encode = enc.encode

    eng_path = "starter_kit/corpus_sample/eng_sample.txt"
    hin_path = "starter_kit/corpus_sample/hin_sample.txt"

    eng_lines = load_data(eng_path)
    hin_lines = load_data(hin_path)

    print("=" * 60)
    print("VERIFIED BASELINE (fertility.py as written):")
    base_eng_fert, base_eng_tpc = baseline_analyze(eng_lines, encode)
    base_hin_fert, base_hin_tpc = baseline_analyze(hin_lines, encode)
    base_ratio = base_hin_fert / base_eng_fert
    print(f"eng: fertility={base_eng_fert:.4f}, tok/char={base_eng_tpc:.4f}")
    print(f"hin: fertility={base_hin_fert:.4f}, tok/char={base_hin_tpc:.4f}")
    print(f"Ratio hin/eng: {base_ratio:.4f}x (baseline reported: 5.89x)")

    print("\n" + "=" * 60)
    print("EXPERIMENT 1: split(' ') vs split()")
    clean_eng_fert, clean_eng_tpc = experiment_split_clean(eng_lines, encode)
    clean_hin_fert, clean_hin_tpc = experiment_split_clean(hin_lines, encode)
    clean_ratio = clean_hin_fert / clean_eng_fert
    print(f"eng (clean split): fertility={clean_eng_fert:.4f} (delta: {clean_eng_fert - base_eng_fert:+.4f})")
    print(f"hin (clean split): fertility={clean_hin_fert:.4f} (delta: {clean_hin_fert - base_hin_fert:+.4f})")
    print(f"Ratio hin/eng: {clean_ratio:.4f}x (delta: {clean_ratio - base_ratio:+.4f}x)")

    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Macro-average vs Micro-average (sum(tok)/sum(word))")
    eng_micro_sp, eng_micro_cl, eng_micro_tpc = experiment_micro_average(eng_lines, encode)
    hin_micro_sp, hin_micro_cl, hin_micro_tpc = experiment_micro_average(hin_lines, encode)
    print(f"eng micro-average (split clean): fertility={eng_micro_cl:.4f} vs macro={clean_eng_fert:.4f} (delta: {eng_micro_cl - clean_eng_fert:+.4f})")
    print(f"hin micro-average (split clean): fertility={hin_micro_cl:.4f} vs macro={clean_hin_fert:.4f} (delta: {hin_micro_cl - clean_hin_fert:+.4f})")
    print(f"Micro-average ratio: {hin_micro_cl / eng_micro_cl:.4f}x vs Macro ratio: {clean_ratio:.4f}x")

    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Impact of line.lower()")
    case_eng_fert, case_eng_tpc = experiment_casing(eng_lines, encode)
    case_hin_fert, case_hin_tpc = experiment_casing(hin_lines, encode)
    print(f"eng without lower(): fertility={case_eng_fert:.4f} vs base={base_eng_fert:.4f} (delta: {case_eng_fert - base_eng_fert:+.4f})")
    print(f"hin without lower(): fertility={case_hin_fert:.4f} vs base={base_hin_fert:.4f} (delta: {case_hin_fert - base_hin_fert:+.4f})")

    print("\n" + "=" * 60)
    print("EXPERIMENT 4: Denominator breakdown on starter corpus")
    for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
        total_tokens = sum(len(encode(l.lower())) for l in lines)
        total_words = sum(len(l.lower().split()) for l in lines)
        total_codepoints = sum(len(l.lower()) for l in lines)
        total_bytes = sum(len(l.lower().encode('utf-8')) for l in lines)
        print(f"[{lang}] Total tokens: {total_tokens}")
        print(f"  tok / word:       {total_tokens / total_words:.4f}")
        print(f"  tok / codepoint:  {total_tokens / total_codepoints:.4f}")
        print(f"  tok / UTF-8 byte: {total_tokens / total_bytes:.4f}")

if __name__ == "__main__":
    main()
