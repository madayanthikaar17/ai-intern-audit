# STRATEGIC DECISION MEMORANDUM

**TO:** Product & Engineering Leadership  
**FROM:** AI Auditing & Serving Team  
**DATE:** September 6, 2026  
**SUBJECT:** Recommendation for Indic Response Casualization Across 6 Languages  

---

### 1. CONSTRAINTS & EVIDENCE TAXONOMY

To ensure defensibility, all inputs are categorized by evidence type:
* `[KNOWN FACT]` Hardware constraint: Exactly 1× NVIDIA A100-80GB GPU available for 2 weeks.
* `[KNOWN FACT]` Budget constraint: $0 external API budget (no commercial LLM synthetic data generation).
* `[KNOWN FACT]` Reviewer coverage: 1 native speaker covering **Hindi and Kannada only** (0% native coverage for Tamil, Telugu, Bengali, and Marathi).
* `[KNOWN FACT]` Reviewer availability: 10 hours/week for 2 weeks = **20 total review hours** (Week 3 is reserved for launch review).
* `[ASSUMPTION]` Human evaluation velocity: A reviewer takes ~3 minutes per response to evaluate tone naturalness, dialect fidelity, and honorific safety $\implies$ **20 response evaluations per hour**.
* `[PLANNING ASSUMPTION]` SFT dataset target: A planning assumption of 3,000 pairs/language across 6 languages = **18,000 total pairs** `[DERIVED]`. (This is an engineering planning assumption, not an assignment requirement).
* `[ASSUMPTION]` Prompt token expansion: Adding casual persona instructions and 2 few-shot exemplars adds ~180 prompt tokens.

---

### 2. BACK-OF-THE-ENVELOPE ARITHMETIC

1. **Reviewer Evaluation Capacity**:
   $$\text{Total Review Capacity} = 20 \text{ hours} \times 20 \text{ responses/hour} = \mathbf{400 \text{ total evaluated responses}} \quad \text{[DERIVED]}$$
   Allocated evenly: **200 responses for Hindi** and **200 responses for Kannada** `[DERIVED]`.

2. **Option A (SFT on Synthetic Pairs) Viability**:
   * Reviewing 400 pairs against an 18,000-pair corpus (`[PLANNING ASSUMPTION]`) leaves **97.8% of training data completely unvalidated** `[DERIVED]`.
   * For Tamil, Telugu, Bengali, and Marathi, **100% of data would be unverified synthetic text** `[DERIVED]`.
   * **Risk**: Unvalidated casualization creates review risk, particularly around honorifics, pronouns, and culturally appropriate register (e.g., disrespectful *tu* vs. *aap* in Hindi, or *neenu* vs. *neevu* in Kannada).

3. **Option B ($\le 1$B Rewriter) Serving Impact**:
   * Running a secondary 1B autoregressive model pass over ~200 output tokens is estimated to add ~15–25 ms/token decode latency $\approx \mathbf{+3.0\text{ to }5.0\text{s}}$ end-to-end latency `[ESTIMATE]` (requires target-stack benchmarking).
   * Reserving ~2 GB VRAM for weights `[ESTIMATE]` reduces available KV cache; actual serving memory footprint also depends on runtime context, activations, and KV cache overhead `[ESTIMATE]`. Any concurrency reduction estimate requires empirical benchmarking.

4. **Option C (Prompt Engineering) Serving Impact**:
   * Adding ~180 prompt tokens `[ASSUMPTION]` adds an estimated ~10–15 ms to prefill latency `[ESTIMATE]` (token count alone does not establish latency; target-stack benchmarking is required).
   * Prompt engineering adds no model weights, but its end-to-end latency impact must be measured on the target serving stack.

---

### 3. RECOMMENDATION: OPTION C (PROMPT ENGINEERING / IN-CONTEXT CASUALIZATION)

We recommend **Option C: In-Context Persona & Few-Shot Prompt Engineering**.

Option C is preferred because it:
- **is reversible**,
- **fits the 2-week / 1-A100 constraint**,
- **requires no additional model deployment**,
- **avoids training on largely unvalidated data**,
- **allows native Hindi/Kannada reviewers to provide feedback before launch**.

*(Note: Option C is not experimentally proven to be best; the Day-1 experiment is intended to validate it).*

---

### 4. SUCCESS METRICS & DECISION THRESHOLDS

* **Primary Metric**: **Casual Naturalness Win-Rate** (Blind A/B test: Casualized vs. Current Baseline).
* **Launch Target**: **$\ge 75\%$ Win-Rate** in Hindi and Kannada `[DECISION THRESHOLD]`, with **$< 1\%$ honorific/safety violations** `[DECISION THRESHOLD]`.
* **Kill Criterion**: If by **Day 8 (End of Week 1)**, the reviewer-assessed win-rate on Hindi/Kannada fails to achieve **$\ge 60\%$** `[DECISION THRESHOLD]`, or if tone casualization causes instruction-following or safety regressions **$> 3\%$** `[DECISION THRESHOLD]`.
* **Action upon Kill**: Freeze informal tone deployment; retain standard polite responses while requesting native reviewer staffing for all 6 languages.

---

### 5. PROPOSED DAY-1 EXPERIMENT

*(Proposed experiment to validate Option C, not completed evidence)*:
* **Setup**: Co-create 5 authentic casual exemplars per language for Hindi and Kannada with the native reviewer.
* **Test Execution**: Run prompt variants across 50 standard user queries, generating 100 total outputs (50 Hindi, 50 Kannada).
* **Evaluation**: Native reviewer scores the 100 outputs for naturalness, formality, and safety to establish baseline viability before full development.
