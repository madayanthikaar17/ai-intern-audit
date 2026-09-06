#!/usr/bin/env python3
"""
partA/corrected_analysis.py -- Corrected multilingual tokenizer analysis on A1 FLORES corpus.

Compares:
  - gpt2 (tiktoken baseline -- English-centric)
  - ai4bharat/IndicBERTv2-MLM-only (Indic-specialized tokenizer)
  - Qwen/Qwen2.5-0.5B (modern multilingual LLM tokenizer)

Across 4 languages:
  - eng (English)
  - hin (Hindi)
  - tam (Tamil)
  - kan (Kannada)

Across 5 denominators:
  - Tokens / Parallel Sentence (Semantic content held constant)
  - Tokens / Whitespace Word
  - Tokens / Grapheme Cluster (Unicode UAX #29 \X)
  - Tokens / UTF-8 Byte (Digital storage held constant)
  - Tokens / Unicode Codepoint (len(line))
"""

import os
import csv
import json
import unicodedata
import regex
import tiktoken
from transformers import AutoTokenizer

LANGUAGES = ["eng", "hin", "tam", "kan"]

def load_corpus(corpus_dir="your-submission/partA/corpus"):
    corpus = {}
    for lang in LANGUAGES:
        path = os.path.join(corpus_dir, f"{lang}.txt")
        with open(path, "r", encoding="utf-8") as f:
            lines = [unicodedata.normalize("NFC", line.strip()) for line in f if line.strip()]
        corpus[lang] = lines
    return corpus

def get_encoders():
    encoders = {}
    
    # 1. GPT-2
    enc_gpt2 = tiktoken.get_encoding("gpt2")
    encoders["gpt2"] = lambda s: enc_gpt2.encode(s)
    
    # 2. IndicBERTv2
    tok_indic = AutoTokenizer.from_pretrained("ai4bharat/IndicBERTv2-MLM-only")
    encoders["IndicBERTv2"] = lambda s: tok_indic.encode(s, add_special_tokens=False)
    
    # 3. Qwen2.5
    tok_qwen = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B")
    encoders["Qwen2.5"] = lambda s: tok_qwen.encode(s, add_special_tokens=False)
    
    return encoders

def count_graphemes(text: str) -> int:
    return len(regex.findall(r"\X", text))

def run_evaluation(corpus, encoders):
    results = []
    
    for tok_name, encode_fn in encoders.items():
        print(f"Evaluating {tok_name} across {len(LANGUAGES)} languages...")
        for lang in LANGUAGES:
            lines = corpus[lang]
            n_sents = len(lines)
            
            total_tokens = 0
            total_words = 0
            total_graphemes = 0
            total_bytes = 0
            total_chars = 0
            
            for line in lines:
                toks = encode_fn(line)
                total_tokens += len(toks)
                total_words += len(line.split())
                total_graphemes += count_graphemes(line)
                total_bytes += len(line.encode("utf-8"))
                total_chars += len(line)
                
            entry = {
                "tokenizer": tok_name,
                "language": lang,
                "sentences": n_sents,
                "total_tokens": total_tokens,
                "total_words": total_words,
                "total_graphemes": total_graphemes,
                "total_bytes": total_bytes,
                "total_codepoints": total_chars,
                "tok_per_sentence": round(total_tokens / n_sents, 2),
                "tok_per_word": round(total_tokens / total_words, 3),
                "tok_per_grapheme": round(total_tokens / total_graphemes, 3),
                "tok_per_byte": round(total_tokens / total_bytes, 3),
                "tok_per_codepoint": round(total_tokens / total_chars, 3)
            }
            results.append(entry)
            
    return results

def compute_cross_lingual_ratios(results):
    ratios = []
    tokenizers = sorted(list(set(r["tokenizer"] for r in results)))
    
    for tok in tokenizers:
        eng_row = next(r for r in results if r["tokenizer"] == tok and r["language"] == "eng")
        for lang in LANGUAGES:
            row = next(r for r in results if r["tokenizer"] == tok and r["language"] == lang)
            ratio_entry = {
                "tokenizer": tok,
                "language": lang,
                "ratio_per_sentence": round(row["tok_per_sentence"] / eng_row["tok_per_sentence"], 2),
                "ratio_per_word": round(row["tok_per_word"] / eng_row["tok_per_word"], 2),
                "ratio_per_grapheme": round(row["tok_per_grapheme"] / eng_row["tok_per_grapheme"], 2),
                "ratio_per_byte": round(row["tok_per_byte"] / eng_row["tok_per_byte"], 2),
                "ratio_per_codepoint": round(row["tok_per_codepoint"] / eng_row["tok_per_codepoint"], 2)
            }
            ratios.append(ratio_entry)
            
    return ratios

def main():
    corpus = load_corpus()
    encoders = get_encoders()
    results = run_evaluation(corpus, encoders)
    ratios = compute_cross_lingual_ratios(results)
    
    out_dir = "your-submission/partA/results"
    os.makedirs(out_dir, exist_ok=True)
    
    # Save CSVs
    fert_csv = os.path.join(out_dir, "corrected_fertility.csv")
    with open(fert_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
        
    ratio_csv = os.path.join(out_dir, "cross_lingual_ratios.csv")
    with open(ratio_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ratios[0].keys()))
        writer.writeheader()
        writer.writerows(ratios)
        
    print("\n" + "=" * 105)
    print(f"{'Tokenizer':<15}{'Lang':<6}{'Total Tokens':>14}{'Tok/Sent':>12}{'Tok/Word':>12}{'Tok/Graph':>12}{'Tok/Byte':>12}{'Tok/Codepoint':>14}")
    print("-" * 105)
    for r in results:
        print(f"{r['tokenizer']:<15}{r['language']:<6}{r['total_tokens']:>14,}{r['tok_per_sentence']:>12.1f}{r['tok_per_word']:>12.2f}{r['tok_per_grapheme']:>12.2f}{r['tok_per_byte']:>12.3f}{r['tok_per_codepoint']:>14.3f}")
        
    print("\n" + "=" * 95)
    print("CROSS-LINGUAL RATIOS RELATIVE TO ENGLISH (English = 1.00x)")
    print("=" * 95)
    print(f"{'Tokenizer':<15}{'Lang':<6}{'x Tok/Sentence':>18}{'x Tok/Word':>14}{'x Tok/Grapheme':>16}{'x Tok/Byte':>14}")
    print("-" * 95)
    for r in ratios:
        print(f"{r['tokenizer']:<15}{r['language']:<6}{r['ratio_per_sentence']:>18.2f}x{r['ratio_per_word']:>14.2f}x{r['ratio_per_grapheme']:>16.2f}x{r['ratio_per_byte']:>14.2f}x")

if __name__ == "__main__":
    main()
