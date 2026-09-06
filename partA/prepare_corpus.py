#!/usr/bin/env python3
"""
partA/prepare_corpus.py -- Fetch, verify, extract, and document the multilingual evaluation corpus.

Target Languages:
  - English: eng_Latn
  - Hindi: hin_Deva
  - Tamil: tam_Taml
  - Kannada: kan_Knda

Source: FLORES-200 / Meta AI NLLB evaluation benchmark
Archive: https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz
"""

import os
import io
import csv
import tarfile
import urllib.request
import unicodedata

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
LANG_MAP = {
    "eng": "eng_Latn",
    "hin": "hin_Deva",
    "tam": "tam_Taml",
    "kan": "kan_Knda"
}

def download_archive(cache_path: str = "your-submission/partA/.flores_cache.tar.gz") -> bytes:
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        print(f"Loading cached archive from {cache_path}...")
        with open(cache_path, "rb") as f:
            return f.read()
    
    print(f"Downloading FLORES-200 archive from {FLORES_URL} (~24.4 MB)...")
    req = urllib.request.Request(FLORES_URL, headers={"User-Agent": "AuditBot/1.0"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "wb") as f:
        f.write(data)
    print(f"Archive cached to {cache_path} ({len(data)} bytes).")
    return data

def inspect_and_extract(archive_bytes: bytes, split: str = "devtest"):
    raw_texts = {}
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
        members = {m.name.lstrip("./"): m for m in tar.getmembers() if m.isfile()}
        
        # Check available splits
        splits_found = set()
        for name in members.keys():
            parts = name.split("/")
            if len(parts) >= 2:
                splits_found.add(parts[1])
        print(f"Available splits in archive: {sorted(list(splits_found))}")
        
        for lang, flores_code in LANG_MAP.items():
            expected_path = f"flores200_dataset/{split}/{flores_code}.{split}"
            if expected_path not in members:
                raise KeyError(f"Expected file {expected_path} not found in archive!")
            
            f = tar.extractfile(members[expected_path])
            lines = [line.decode("utf-8").strip() for line in f.readlines()]
            raw_texts[lang] = lines
            print(f"Extracted {lang} ({flores_code}): {len(lines)} sentences from '{split}' split.")
            
    # Verify exact alignment and identical row count
    counts = {lang: len(lines) for lang, lines in raw_texts.items()}
    if len(set(counts.values())) != 1:
        raise ValueError(f"Mismatched sentence counts: {counts}")
    
    # NFC normalize each sentence
    normalized_texts = {}
    for lang, lines in raw_texts.items():
        normalized_texts[lang] = [unicodedata.normalize("NFC", l) for l in lines]
        
    return normalized_texts

def save_and_compute_stats(corpus: dict, output_dir: str = "your-submission/partA/corpus"):
    os.makedirs(output_dir, exist_ok=True)
    stats = []
    
    print("\n" + "=" * 95)
    print(f"{'Language':<10}{'ISO Code':<12}{'Sentences':>10}{'Words(ws)':>12}{'Codepoints':>12}{'UTF-8 Bytes':>14}{'Avg Words/S':>12}{'Avg Bytes/S':>12}")
    print("-" * 95)
    
    for lang, lines in corpus.items():
        file_path = os.path.join(output_dir, f"{lang}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(l + "\n")
        
        n_sents = len(lines)
        total_words = sum(len(l.split()) for l in lines)
        total_codepoints = sum(len(l) for l in lines)
        total_bytes = sum(len(l.encode("utf-8")) for l in lines)
        avg_words = total_words / n_sents
        avg_bytes = total_bytes / n_sents
        
        stat_entry = {
            "language": lang,
            "flores_code": LANG_MAP[lang],
            "sentences": n_sents,
            "whitespace_words": total_words,
            "unicode_codepoints": total_codepoints,
            "utf8_bytes": total_bytes,
            "avg_words_per_sentence": round(avg_words, 2),
            "avg_bytes_per_sentence": round(avg_bytes, 2)
        }
        stats.append(stat_entry)
        
        print(f"{lang:<10}{LANG_MAP[lang]:<12}{n_sents:>10}{total_words:>12}{total_codepoints:>12}{total_bytes:>14}{avg_words:>12.2f}{avg_bytes:>12.2f}")
        
    stats_csv_path = "your-submission/partA/corpus_stats.csv"
    with open(stats_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats[0].keys()))
        writer.writeheader()
        writer.writerows(stats)
    print(f"\nCorpus files saved to: {output_dir}")
    print(f"Corpus statistics saved to: {stats_csv_path}")

if __name__ == "__main__":
    archive = download_archive()
    corpus = inspect_and_extract(archive, split="devtest")
    save_and_compute_stats(corpus)
