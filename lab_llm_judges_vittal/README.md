# LAB | LLMs grading LLMs — with receipts

## Scenario

**Meridian Community Bank** (fictional) wants to use an LLM to draft first-pass ECOA/Reg
B-compliant adverse-action (loan rejection) letters, reviewed by a human loan officer before
sending. Full scenario details: [00-scenario.md](00-scenario.md).

## Approach

1. Audited 3 existing public benchmarks (MMLU, TruthfulQA, BBQ) against this specific use case —
   none were usable as-is; see [benchmark_audit.md](benchmark_audit.md) for why, and what's
   reusable from each.
2. Designed a custom 5-prompt mini-benchmark covering the actual failure surface (completeness
   of disclosed reasons, hallucinated reasons, fair-lending bias, over-disclosure under
   adversarial pressure, non-English fidelity), plus a full LLM-as-judge prompt with bias
   analysis and a calibration plan: [evaluation_design.md](evaluation_design.md).
3. Wrote a client-facing evaluation memo with appropriate hedging and caveats:
   [evaluation_memo.md](evaluation_memo.md).
4. Reflected on cross-language evaluation, the "is this AGI-level" question, and where human
   review is non-negotiable: [reflection.md](reflection.md).
5. Implemented the judge prompt as a working Python pipeline against the OpenAI API:
   [llm_judge_evaluation.py](llm_judge_evaluation.py), with results in
   [evaluation_results.json](evaluation_results.json) and a build summary in
   [implementation_summary.md](implementation_summary.md).

## File map

| File | What it is |
|---|---|
| `00-scenario.md` | Client scenario (Step 1) |
| `benchmark_audit.md` | 3 benchmark evaluation cards (Step 2) |
| `evaluation_design.md` | 5 custom eval prompts + full LLM-as-judge prompt with bias/calibration analysis (Steps 3-4) |
| `evaluation_memo.md` | 1-page client memo (Step 5) |
| `reflection.md` | 3 reflection questions (Step 6) |
| `llm_judge_evaluation.py` | Implementation of the judge pipeline (Steps 7-10) |
| `evaluation_results.json` | Output of a pipeline run (currently mock-mode — see caveat below) |
| `implementation_summary.md` | What was built and key findings (Step 11) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for the required `OPENAI_API_KEY` env var |

## How to run

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env and add your real OPENAI_API_KEY
python llm_judge_evaluation.py
```

If `OPENAI_API_KEY` is not set, the script automatically runs in **mock mode** (no API calls, no
cost) so the pipeline can be validated end-to-end without a key — mock outputs are clearly
labeled `"mock": true` in the JSON and are not real evaluation evidence. The
`evaluation_results.json` committed in this repo is a **live run** against `gpt-4o-mini`
(`"mock": false`) — all 5 cases scored 5/5; see `implementation_summary.md` for why that ceiling
result should be read with skepticism (small sample, same-model judge/generator) rather than as
a clean bill of health.
