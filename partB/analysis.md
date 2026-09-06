# Part B2, B3, B4: Serving Anomaly, Output Rate Reconciliation, and Telemetry

---

## Executive Summary: Answers to Core Part B Questions

- **B1 (Theoretical KV-Cache Capacity)**:
  Under decimal GB accounting ($10^9$ bytes), the available KV pool is **12.08 GB** ($105,329\text{ tokens}$), fitting **25 complete 4096-token sequences** `[DERIVED]`. (Under binary GiB accounting, the capacity is **29 sequences** `[DERIVED]`). This is a **THEORETICAL capacity estimate under stated static allocation assumptions, not an absolute serving limit**. It is verified by `bench_log.csv` at batch 24 where `kv_cache_util = 0.93` ($24 / 0.93 \approx 25.8$ sequences) and batches 32 and 48 preempt exactly 7 and 23 sequences `[MEASURED]`.
- **B2 (Throughput Scaling Anomaly)**:
  **"Increasing batch size beyond the KV-cache capacity causes preemption/recomputation pressure, so throughput no longer scales monotonically with batch size."** When active requests exceed KV cache capacity, the engine preempts active sequences, evicting KV blocks and requiring full recomputation, which destroys useful throughput.
- **B3 (Misread Column & Corrected Interpretation)**:
  The old report misread **`reported_tok_s`**, which computes $\frac{\text{num\_requests} \times (\text{prompt\_len} + \text{gen\_len})}{\text{wall\_clock\_s}}$ `[DERIVED]`. Because it sums prompt tokens processed in parallel prefill with generated tokens, it created the illusion that long prompts improve GPU utilization. In reality, generated-token rate for long prompts was 44% lower (163.9 tok/s vs 294.5 tok/s at batch 16 `[DERIVED]`). At batch 24, the **End-to-end generated-token rate is 200.92 tok/s** `[DERIVED]` and the **Steady-state decode rate inferred from ITL is 249.82 tok/s** `[DERIVED]`.
- **B4 (Production Monitoring Counter)**:
  **"Production should monitor the serving engine's KV-cache preemption/recomputation counter. If the production stack is vLLM, `num_preemptions_total` is an appropriate concrete counter; otherwise use the equivalent counter exposed by the actual serving engine."** Its purpose is to detect when increasing concurrency causes KV-cache pressure and preemption/recomputation.

---

## B2: Long-Context Throughput Anomaly (Prompt = 3584, Gen = 512)

### 1. Identifying the Anomaly in `bench_log.csv`
Under naive batch scaling, throughput is expected to increase monotonically with batch size until saturating compute and memory bandwidth. However, examining the long-context sweep (prompt length 3584, generation length 512) reveals a performance collapse above batch 24:

| Batch Size | Wall Clock (s) `[MEASURED]` | Reported tok/s `[MEASURED]` | ITL p50 (ms) `[MEASURED]` | Preempted Seqs `[MEASURED]` | KV Cache Util `[MEASURED]` |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 4 | 28.98 | 565.4 | 51.33 | 0 | 0.16 |
| 8 | 36.30 | 902.6 | 62.26 | 0 | 0.31 |
| 16 | 49.97 | 1311.4 | 77.20 | 0 | 0.62 |
| **24 (Peak)** | **61.16** | **1607.4** | **96.07** | **0** | **0.93** |
| **32** | **94.71** | **1384.0 (-13.9%)** | **101.79** | **7** | **0.97** |
| **48** | **151.41** | **1298.5 (-19.2%)** | **100.00** | **23** | **0.97** |

* **The Anomaly**: Between batch 24 and batch 48, throughput drops by **19.2%** (from 1607.4 down to 1298.5 tok/s `[MEASURED]`), while total wall-clock time spikes from 61.16s to 151.41s (+147% `[MEASURED]`).
* **Conclusion**:
  > **"Increasing batch size beyond the KV-cache capacity causes preemption/recomputation pressure, so throughput no longer scales monotonically with batch size."**

### 2. The Mechanism
As derived in B1, the L4 GPU KV cache pool holds approximately 25 full 4096-token sequences under the stated static memory budget.
When the serving stack admits batch 32 or 48 without concurrency throttling:
1. Active requests exhaust the KV cache pool (`kv_cache_util = 0.97` `[MEASURED]`).
2. The scheduler runs out of memory blocks and is forced to **preempt active sequences** (7 sequences at batch 32; 23 sequences at batch 48 `[MEASURED]`).
3. Preempted sequences are evicted (or discarded). When resumed, they must undergo full prefill recomputation, creating severe GPU pipeline bubbles, thrashing memory bandwidth, and reducing useful throughput.

### 3. Proposed Configuration Change & Analytical Prediction
* **Proposed Change**: Configure the serving engine with an admission concurrency cap: `--max-num-seqs 24` (or set max active sequences $\le 24$).
* **Mechanism**: Surplus requests remain queued in host memory before prefill begins, preventing KV-cache overflow and preemption thrashing.
* **Predicted Quantitative Effect [ESTIMATE]**:
  - Processing 48 requests as two clean, non-preempting waves of 24 requests:
    $$\text{Wall-Clock Time} = 2 \times 61.16\text{s} = \mathbf{122.32\text{s}} \quad \text{[ESTIMATE]}$$
  - *(Note: This $122.32\text{s}$ calculation is a simple two-wave estimate, not an observed benchmark measurement. It illustrates the expected 19.2% latency reduction compared to the unconstrained 151.41s run).*
  - Preemptions are predicted to drop from **23 to 0** `[ESTIMATE]`.
  - Effective throughput is predicted to rise from 1298.5 tok/s to **1607.4 tok/s (+23.8%)** `[ESTIMATE]`.

---

## B3: Reverse-Engineering REPORT_v0 Misreading & Output Rate Reconciliation

### 1. Identification of the Misread Column
`REPORT_v0` Section 2 concluded that *"longer prompts clearly give better GPU utilization"* (1311 tok/s vs 883 tok/s at batch 16) and that batch 48 would deliver $\approx 3200\text{ tok/s}$.

Both erroneous conclusions stem from misreading the column **`reported_tok_s`**.

### 2. Reverse-Engineering the Formula [DERIVED]
By testing against multiple rows in `bench_log.csv`, we prove that `reported_tok_s` is defined as:

$$\text{reported\_tok\_s} = \frac{\text{num\_requests} \times (\text{prompt\_len} + \text{gen\_len})}{\text{wall\_clock\_s}} \quad \text{[DERIVED]}$$

* **Verification on Row 1** (Batch 1, Prompt 512, Gen 256):
  $$\frac{1 \times (512 + 256)}{10.94\text{s}} = \frac{768}{10.94} = 70.20 \implies \text{Reported: } \mathbf{70.2} \quad \text{[DERIVED]}$$
* **Verification on Row 6** (Batch 16, Prompt 512, Gen 256):
  $$\frac{16 \times (512 + 256)}{13.91\text{s}} = \frac{12,288}{13.91} = 883.39 \implies \text{Reported: } \mathbf{883.2} \quad \text{[DERIVED]}$$
* **Verification on Row 11** (Batch 16, Prompt 3584, Gen 512):
  $$\frac{16 \times (3584 + 512)}{49.97\text{s}} = \frac{65,536}{49.97} = 1311.51 \implies \text{Reported: } \mathbf{1311.4} \quad \text{[DERIVED]}$$
* **Verification on Row 12** (Batch 24, Prompt 3584, Gen 512):
  $$\frac{24 \times (3584 + 512)}{61.16\text{s}} = \frac{98,304}{61.16} = 1607.33 \implies \text{Reported: } \mathbf{1607.4} \quad \text{[DERIVED]}$$

### 3. How This Misreading Produced False Conclusions
`reported_tok_s` counts **input prompt tokens** as if they were generated tokens. Because prompt tokens are processed in parallel during compute-bound matrix multiplications during the prefill phase (at thousands of tokens/sec), requests with 3584-token prompts artificially inflate the numerator by $7\times$, creating an illusion of high throughput.

In reality, **generated-token rate was substantially lower for long prompts**:
- At batch 16, short prompts generated:
  $$\frac{16 \times 256}{13.91\text{s}} = \mathbf{294.5\text{ gen tok/s}} \quad \text{[DERIVED]}$$
- At batch 16, long prompts generated:
  $$\frac{16 \times 512}{49.97\text{s}} = \mathbf{163.9\text{ gen tok/s}} \quad \text{[DERIVED]}$$
  *(44% lower than the short prompt generation rate!)*

**Key Takeaway**:
The long-prompt case does NOT demonstrate better generation throughput. The old report's interpretation that longer prompts produced better GPU utilization is therefore unsupported by the actual generated-token rate. Long prompts demand substantially larger KV caches, increasing memory traffic during decode and slowing token emission. Furthermore, the linear projection to 3200 tok/s at batch 48 ignored the physical KV cache capacity limit, leading to severe preemption thrashing in reality.

---

### 4. Output Generation Rates for Batch 24 (Long Prompt)

We calculate two distinct generation metrics from the log for batch 24:

#### Metric 1: End-to-End Generated-Token Rate [DERIVED]
Measures the rate of newly minted generation tokens delivered to users over total request duration:

$$\text{End-to-End Gen Rate} = \frac{\text{batch\_size} \times \text{gen\_len}}{\text{wall\_clock\_s}} = \frac{24 \times 512}{61.16\text{s}} = \frac{12,288 \text{ tokens}}{61.16\text{s}} = \mathbf{200.92 \text{ gen tok/s}} \quad \text{[DERIVED]}$$

#### Metric 2: Steady-State Decode Rate Inferred from ITL [DERIVED]
Measures the instantaneous token emission rate strictly during the autoregressive decode phase, utilizing median Inter-Token Latency ($\text{ITL} = 96.07\text{ ms} = 0.09607\text{ s}$ `[MEASURED]`):

$$\text{Steady-State Decode Rate} = \frac{\text{batch\_size}}{\text{ITL (seconds)}} = \frac{24}{0.09607\text{ s}} = \mathbf{249.82 \text{ gen tok/s}} \quad \text{[DERIVED]}$$

#### Why the Two Calculations Differ (Not Interchangeable)
- **End-to-end generated-token rate (200.92 tok/s)** amortizes the initial prefill phase ($\text{TTFT} = 500.5\text{ ms}$ `[MEASURED]`) and batch tail completion variance across the entire $61.16\text{s}$ request lifecycle.
- **Steady-state decode rate inferred from ITL (249.82 tok/s)** measures pure instantaneous generation speed once all sequences are actively decoding in parallel.
- They measure different quantities and are therefore not expected to be identical. Do not treat them as interchangeable.
- Both metrics confirm that actual generation throughput is in the **$200\text{--}250\text{ tok/s}$** range, an order of magnitude lower than the misleading $1607.4\text{ tok/s}$ reported in `REPORT_v0`.

---

## B4: Production Telemetry & Serving Metric

> **Stack-Independent Recommendation**:  
> **"Production should monitor the serving engine's KV-cache preemption/recomputation counter. If the production stack is vLLM, `num_preemptions_total` is an appropriate concrete counter; otherwise use the equivalent counter exposed by the actual serving engine."**

### Purpose of the Counter:
The purpose of the metric is to detect when increasing concurrency causes KV-cache pressure and preemption/recomputation.

### Concrete Implementation Details:
* **vLLM Concrete Counter**: `vllm:num_preemptions_total` (or `vllm:iteration_tokens_total{type="recompute"}`).
* **Other Serving Engines**: In TensorRT-LLM, monitor `kv_cache_preemption_count`; in TGI/Triton, monitor equivalent request-pause/recompute metrics. A vLLM-specific counter is not universally available across all runtimes.
* **Expected Trend**: In healthy operation (concurrency $\le 24$ full-length sequences), this counter remains strictly at **0**. When concurrency exceeds capacity, the counter will spike sharply above 0.
* **Falsification Condition**: If throughput drops at higher batch sizes while preemption counters remain strictly at **0**, the preemption hypothesis is falsified, pointing to alternative bottlenecks such as PCIe host-device bandwidth, CPU tokenization contention, or GPU thermal throttling.
