# AI Usage Record

In accordance with the assignment guidelines, this document provides an honest account of how AI tools were used during this audit.

## Summary of AI Assistance

- **Theoretical learning & clarification:** ChatGPT and Claude were used to understand the theoretical foundations needed for the audit, including tokenizer fertility, Unicode representations, tokenization metrics, KV-cache memory, serving throughput, and goodput.

- **Problem-solving support:** AI was used to discuss possible interpretations of the benchmark results, identify areas that needed further investigation, and help structure the audit.

- **Code assistance:** AI assistance was used for parts of the supporting analysis scripts, including bug-isolation and metric-analysis utilities. The resulting code was executed and checked against the repository data.

- **Documentation support:** AI was used to help organize findings and improve the clarity of the written analysis and decision memo.

## Verification

All reported experimental results were checked by executing the relevant scripts and comparing them with the provided benchmark files and model specification.

No benchmark or throughput values were intentionally fabricated or taken from AI-generated assumptions.

## Examples of Course Corrections

1. **Regex environment issue:** An execution error involving the `regex` package was investigated with AI assistance and traced to a local file shadowing the installed package. Renaming the conflicting file resolved the issue.

2. **Whitespace splitting:** AI suggested investigating the use of `split(" ")`. Inspection of the starter corpus showed repeated spaces, and the resulting change in fertility was then measured experimentally.

3. **Line-weighted fertility:** AI initially described the difference between per-line averaging and aggregate fertility too strongly as an "aggregation bug." After checking the implementation and docstring, this was corrected to a **metric-definition issue**: the code correctly computes the mean of per-line fertility, but this is not the same statistic as aggregate corpus fertility.

