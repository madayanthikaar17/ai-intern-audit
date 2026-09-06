# Part B1: KV-Cache Arithmetic and Theoretical Concurrency

This document derives the theoretical memory footprint and concurrency capacity of the FLM-4B-Instruct model on an NVIDIA L4 GPU, using only the parameters in `bench/model_spec.md`.

---

## 1. Parameters from `model_spec.md`
- **Model Parameters**: 4.2 Billion ($4.2 \times 10^9$)
- **Transformer Layers ($L$)**: 28
- **Hidden Dimension ($d_{model}$)**: 3072
- **Query Attention Heads ($H_Q$)**: 24
- **Key-Value Heads ($H_{KV}$, Grouped-Query Attention)**: 8
- **Head Dimension ($d_h$)**: 128
- **Weight Precision**: fp16 (2 bytes per parameter)
- **KV Cache Precision**: fp16 (2 bytes per element)
- **Max Model Context Length**: 4096 tokens
- **GPU Hardware**: 1× NVIDIA L4 (24 GB VRAM)
- **GPU Memory Utilization Budget**: 0.92 (92%)
- **Non-KV Runtime Overhead**: ~1.6 GB (activations, CUDA graphs, scratch buffers)

---

## 2. Derivation (a): Exact KV-Cache Bytes per Token [DERIVED]

In Transformer self-attention, each token requires storing both a **Key (K)** vector and a **Value (V)** vector for every layer across all KV attention heads.

$$\text{KV Bytes / Token} = 2 \times L \times H_{KV} \times d_h \times \text{Bytes per Element} \quad \text{[DERIVED]}$$

Where:
- Factor of $2$: One vector for Key, one vector for Value.
- $L = 28$ layers.
- $H_{KV} = 8$ heads (under Grouped-Query Attention).
- $d_h = 128$ dimensions per head.
- $\text{Bytes per Element} = 2$ (fp16 precision).

$$\text{KV Bytes / Token} = 2 \times 28 \times 8 \times 128 \times 2 = \mathbf{114,688 \text{ bytes}} \quad \text{[DERIVED]}$$

Converting to binary units:
$$\frac{114,688 \text{ bytes}}{1,024 \text{ bytes/KiB}} = \mathbf{112.0 \text{ KiB per token}} \quad \text{[DERIVED]}$$

---

## 3. Derivation (b): Theoretical Concurrency Capacity for 4096-Token Sequences [DERIVED]

To establish how many concurrent 4096-token sequences can fit in GPU memory, we calculate the memory available for the dynamic KV cache allocator after fixed allocations.

### Step 1: Model Weight Memory [DERIVED]
$$\text{Weight Footprint} = 4.2 \times 10^9 \text{ parameters} \times 2 \text{ bytes/param} = \mathbf{8.40 \text{ GB}} \quad \text{[DERIVED]}$$

### Step 2: Memory Budget Accounting (Decimal GB vs. Binary GiB)

Because hardware vendors specify memory in decimal gigabytes ($1 \text{ GB} = 10^9 \text{ bytes}$) while operating systems often report memory in binary gibibytes ($1 \text{ GiB} = 2^{30} \text{ bytes} = 1,073,741,824 \text{ bytes}$), we calculate both interpretations:

#### Interpretation A: Decimal Accounting ($1 \text{ GB} = 10^9 \text{ bytes}$) [DERIVED]
1. **Total Available GPU Memory**:
   $$24.0 \text{ GB} \times 0.92 = \mathbf{22.08 \text{ GB}} = 22,080,000,000 \text{ bytes} \quad \text{[DERIVED]}$$
2. **Fixed Deductions**:
   - Model weights: $- 8.40 \text{ GB} = - 8,400,000,000 \text{ bytes}$
   - Non-KV runtime overhead: $- 1.60 \text{ GB} = - 1,600,000,000 \text{ bytes}$
3. **Available KV Cache Pool**:
   $$22.08 - 8.40 - 1.60 = \mathbf{12.08 \text{ GB}} = 12,080,000,000 \text{ bytes} \quad \text{[DERIVED]}$$
4. **Maximum Total Tokens**:
   $$\text{Max Tokens} = \frac{12,080,000,000 \text{ bytes}}{114,688 \text{ bytes/token}} \approx \mathbf{105,329.2 \text{ tokens}} \quad \text{[DERIVED]}$$
5. **Full 4096-Token Sequence Concurrency**:
   $$\text{Max Sequences} = \frac{105,329.2 \text{ tokens}}{4096 \text{ tokens/seq}} \approx \mathbf{25.72 \implies 25 \text{ complete 4096-token sequences (floor)}} \quad \text{[DERIVED]}$$

#### Interpretation B: Binary Accounting ($1 \text{ GiB} = 2^{30} \text{ bytes}$) [DERIVED]
1. **Total Available GPU Memory**:
   $$24 \times 1,073,741,824 \times 0.92 = 23,708,219,474 \text{ bytes} \approx 22.08 \text{ GiB} \quad \text{[DERIVED]}$$
2. **Minus Weights and Overhead**:
   $$23,708,219,474 - 8,400,000,000 - 1,600,000,000 = 13,708,219,474 \text{ bytes} \approx 12.77 \text{ GiB} \quad \text{[DERIVED]}$$
3. **Maximum Total Tokens**:
   $$\text{Max Tokens} = \frac{13,708,219,474}{114,688} \approx \mathbf{119,526.2 \text{ tokens}} \quad \text{[DERIVED]}$$
4. **Full 4096-Token Sequence Concurrency**:
   $$\text{Max Sequences} = \frac{119,526.2}{4096} \approx \mathbf{29.18 \implies 29 \text{ complete 4096-token sequences (floor)}} \quad \text{[DERIVED]}$$

---

## 4. Reconciling Prediction Against `bench_log.csv`

Inspecting `bench_log.csv` provides decisive empirical evidence of which accounting convention the benchmarked serving stack implemented:
- At **Batch 24** (prompt $3584 + 512 = 4096$ tokens):
  The benchmark records `[MEASURED]`:
  $$\text{kv\_cache\_util} = \mathbf{0.93} \quad \text{[MEASURED]}$$
  If 24 sequences occupy 93% of the KV cache, the 100% capacity is `[DERIVED]`:
  $$\text{Full Capacity} = \frac{24}{0.93} \approx \mathbf{25.8 \text{ sequences}} \quad \text{[DERIVED]}$$
  This aligns with the **Decimal GB prediction ($25.72$ sequences)** with 99.7% precision.
- Furthermore:
  - At **Batch 32**, exactly **7 sequences** are preempted `[MEASURED]` ($32 - 25 = 7$).
  - At **Batch 48**, exactly **23 sequences** are preempted `[MEASURED]` ($48 - 25 = 23$).

---

## 5. Capacity Interpretation: Theoretical Estimate vs. Absolute Serving Limit

**Important Distinction**:
The value of **25 complete 4096-token sequences** is a **THEORETICAL capacity estimate under the stated assumptions** (static full-length 4096-token allocation, decimal GB accounting, and 1.6 GB runtime overhead), **not an absolute serving limit**.

In real-world serving:
1. **Dynamic Paged Allocation (PagedAttention)**: Schedulers allocate KV blocks incrementally token-by-token. When requests have variable lengths or shorter prompts, the active sequence concurrency can be substantially higher than 25.
2. **Fragmentation & Safety Margins**: Non-contiguous block allocation can introduce slight memory fragmentation, and production schedulers typically reserve a safety margin (5–10% of KV blocks) to absorb token generation bursts without triggering eviction.

**Summary**:
- **Theoretical Capacity**: 105,329 tokens $\approx$ **25 complete 4096-token sequences** under decimal GB convention `[DERIVED]`.
- **Benchmark Agreement**: Directly confirmed by batch 24 utilization (0.93 $\implies 25.8$ seqs) and exact preemption counts at batch 32 (7 preemptions) and batch 48 (23 preemptions) `[MEASURED]`.
