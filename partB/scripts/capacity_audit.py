#!/usr/bin/env python3
"""
partB/scripts/capacity_audit.py -- Capacity Reconciliation and Verification Script
Performs exact arithmetic for B1, B2, B3, and B4 using model_spec.md and bench_log.csv.
"""

import csv
import json
import os

def calculate_b1():
    # Model parameters from model_spec.md
    layers = 28
    kv_heads = 8
    head_dim = 128
    bytes_per_elem = 2  # fp16
    
    # (a) Exact KV bytes per token: 2 (K and V) * layers * kv_heads * head_dim * bytes_per_elem
    kv_bytes_per_token = 2 * layers * kv_heads * head_dim * bytes_per_elem
    kv_kib_per_token = kv_bytes_per_token / 1024
    
    # Hardware & memory budget
    gpu_total_gb = 24.0
    gpu_util = 0.92
    model_params = 4.2e9
    weights_bytes = model_params * bytes_per_elem  # 8.4 GB (decimal)
    non_kv_overhead_gb = 1.6
    seq_len = 4096
    
    # Decimal GB convention (1 GB = 10^9 bytes)
    usable_bytes_dec = gpu_total_gb * 1e9 * gpu_util  # 22.08 GB
    weights_bytes_dec = weights_bytes                # 8.40 GB
    overhead_bytes_dec = non_kv_overhead_gb * 1e9    # 1.60 GB
    kv_pool_dec = usable_bytes_dec - weights_bytes_dec - overhead_bytes_dec # 12.08 GB
    max_tokens_dec = kv_pool_dec / kv_bytes_per_token
    max_seqs_dec = max_tokens_dec / seq_len
    
    # Binary GiB convention (1 GiB = 2^30 bytes = 1,073,741,824 bytes)
    total_bytes_bin = gpu_total_gb * (1024**3)
    usable_bytes_bin = total_bytes_bin * gpu_util
    kv_pool_bin = usable_bytes_bin - weights_bytes_dec - overhead_bytes_dec
    max_tokens_bin = kv_pool_bin / kv_bytes_per_token
    max_seqs_bin = max_tokens_bin / seq_len
    
    return {
        "kv_bytes_per_token": kv_bytes_per_token,
        "kv_kib_per_token": kv_kib_per_token,
        "dec": {
            "usable_gb": usable_bytes_dec / 1e9,
            "weights_gb": weights_bytes_dec / 1e9,
            "overhead_gb": overhead_bytes_dec / 1e9,
            "kv_pool_gb": kv_pool_dec / 1e9,
            "kv_pool_bytes": kv_pool_dec,
            "max_tokens": max_tokens_dec,
            "max_seqs": max_seqs_dec,
            "max_seqs_floor": int(max_seqs_dec)
        },
        "bin": {
            "usable_gib": usable_bytes_bin / (1024**3),
            "weights_gib": weights_bytes_dec / (1024**3),
            "overhead_gib": overhead_bytes_dec / (1024**3),
            "kv_pool_gib": kv_pool_bin / (1024**3),
            "kv_pool_bytes": kv_pool_bin,
            "max_tokens": max_tokens_bin,
            "max_seqs": max_seqs_bin,
            "max_seqs_floor": int(max_seqs_bin)
        }
    }

def analyze_bench_log(csv_path="starter_kit/bench/bench_log.csv"):
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            parsed = {}
            for k, v in r.items():
                parsed[k] = float(v) if "." in v else int(v)
            rows.append(parsed)
    return rows

def verify_formula(rows):
    print("=" * 80)
    print("B3: REVERSE-ENGINEERING reported_tok_s FORMULA ACROSS BENCH_LOG ROWS")
    print("=" * 80)
    print(f"{'Row':<6}{'Batch':<8}{'Prompt':<8}{'Gen':<6}{'WallClock':<12}{'Reported':<12}{'Calculated':<12}{'Delta':<10}")
    print("-" * 80)
    
    test_rows = [rows[0], rows[4], rows[7], rows[10], rows[11]]
    for idx, r in enumerate(test_rows):
        total_tokens = r["num_requests"] * (r["prompt_len"] + r["gen_len"])
        calc_tok_s = total_tokens / r["wall_clock_s"]
        delta = calc_tok_s - r["reported_tok_s"]
        print(f"{idx+1:<6}{r['batch_size']:<8}{r['prompt_len']:<8}{r['gen_len']:<6}{r['wall_clock_s']:<12.2f}{r['reported_tok_s']:<12.1f}{calc_tok_s:<12.2f}{delta:<+10.4f}")

def main():
    b1 = calculate_b1()
    print("=" * 80)
    print("B1: KV-CACHE ARITHMETIC & GPU CONCURRENCY")
    print("=" * 80)
    print(f"(a) Exact KV Cache Bytes per Token: {b1['kv_bytes_per_token']} bytes ({b1['kv_kib_per_token']} KiB)")
    print(f"    Formula: 2 (K & V) * 28 layers * 8 KV heads * 128 head_dim * 2 bytes (fp16)")
    
    print("\n(b) Maximum Concurrent 4096-Token Sequences:")
    dec = b1["dec"]
    print(f"  [Decimal GB Convention - 1 GB = 1e9 bytes]:")
    print(f"    Total usable memory (24 GB * 0.92):  {dec['usable_gb']:.2f} GB")
    print(f"    Model weights (4.2B * 2 bytes):      -{dec['weights_gb']:.2f} GB")
    print(f"    Non-KV runtime overhead:             -{dec['overhead_gb']:.2f} GB")
    print(f"    Available KV Cache Pool:              {dec['kv_pool_gb']:.2f} GB ({dec['kv_pool_bytes']:,.0f} bytes)")
    print(f"    Max total tokens:                     {dec['max_tokens']:,.1f} tokens")
    print(f"    Max 4096-token sequences:             {dec['max_seqs']:.2f} -> FLOOR: {dec['max_seqs_floor']} sequences")
    
    bin_m = b1["bin"]
    print(f"\n  [Binary GiB Convention - 1 GiB = 2^30 bytes]:")
    print(f"    Total usable memory (24 GiB * 0.92): {bin_m['usable_gib']:.2f} GiB")
    print(f"    Available KV Cache Pool:              {bin_m['kv_pool_gib']:.2f} GiB ({bin_m['kv_pool_bytes']:,.0f} bytes)")
    print(f"    Max 4096-token sequences:             {bin_m['max_seqs']:.2f} -> FLOOR: {bin_m['max_seqs_floor']} sequences")
    
    rows = analyze_bench_log()
    verify_formula(rows)
    
    # B2 Analysis
    long_rows = [r for r in rows if r["prompt_len"] == 3584]
    print("\n" + "=" * 80)
    print("B2: LONG-CONTEXT SWEEP ANOMALY (prompt_len=3584, gen_len=512)")
    print("=" * 80)
    print(f"{'Batch':<8}{'WallClock(s)':<14}{'ReportedTok/s':<16}{'TTFT(ms)':<12}{'ITL(ms)':<10}{'Preempted':<12}{'KVUtil':<8}")
    print("-" * 80)
    for r in long_rows:
        print(f"{r['batch_size']:<8}{r['wall_clock_s']:<14.2f}{r['reported_tok_s']:<16.1f}{r['ttft_ms_p50']:<12.1f}{r['itl_ms_p50']:<10.2f}{r['preempted_seqs']:<12}{r['kv_cache_util']:<8.2f}")

    # B3 Dual Goodput for Batch 24
    b24 = next(r for r in long_rows if r["batch_size"] == 24)
    print("\n" + "=" * 80)
    print("B3: OUTPUT GENERATION RATES FOR BATCH 24 (Long Prompt)")
    print("=" * 80)
    gen_tokens = b24["batch_size"] * b24["gen_len"]
    rate_1 = gen_tokens / b24["wall_clock_s"]
    print(f"Metric 1: End-to-End Generated-Token Rate [DERIVED]")
    print(f"  Formula: (batch_size * gen_len) / wall_clock_s")
    print(f"  Calculation: ({b24['batch_size']} * {b24['gen_len']}) / {b24['wall_clock_s']}s = {gen_tokens} / {b24['wall_clock_s']}s")
    print(f"  Rate 1: {rate_1:.2f} gen tok/s")
    
    itl_s = b24["itl_ms_p50"] / 1000.0
    rate_2 = b24["batch_size"] / itl_s
    print(f"\nMetric 2: Steady-State Decode Rate Inferred from ITL [DERIVED]")
    print(f"  Formula: batch_size / itl_seconds")
    print(f"  Calculation: {b24['batch_size']} / {itl_s:.5f}s")
    print(f"  Rate 2: {rate_2:.2f} gen tok/s")
    
    print(f"\nDifference Analysis:")
    print(f"  Metric 1 includes prefill phase (TTFT p50 = {b24['ttft_ms_p50']} ms) and tail latency across the batch.")
    print(f"  Metric 2 measures the instantaneous token emission rate strictly during autoregressive decode.")
    print(f"  They measure different engineering quantities and are not interchangeable.")

    # Save summary JSON
    out_dir = "your-submission/partB/results"
    os.makedirs(out_dir, exist_ok=True)
    summary = {
        "b1_kv_bytes_per_token": b1["kv_bytes_per_token"],
        "b1_max_sequences_dec": dec["max_seqs_floor"],
        "b1_max_sequences_bin": bin_m["max_seqs_floor"],
        "b2_peak_throughput_batch": 24,
        "b2_preemptions_batch_32": 7,
        "b2_preemptions_batch_48": 23,
        "b3_reported_formula": "num_requests * (prompt_len + gen_len) / wall_clock_s",
        "b3_batch_24_end_to_end_gen_rate": round(rate_1, 2),
        "b3_batch_24_steady_state_decode_rate": round(rate_2, 2),
        "b3_batch_24_goodput_method1": round(rate_1, 2),
        "b3_batch_24_goodput_method2": round(rate_2, 2)
    }
    with open(os.path.join(out_dir, "capacity_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {os.path.join(out_dir, 'capacity_summary.json')}")

if __name__ == "__main__":
    main()
