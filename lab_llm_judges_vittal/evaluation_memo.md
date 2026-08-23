TO: Meridian Community Bank — Consumer Lending Compliance Team
FROM: Vittal Navale, LLM Evaluation Consultant
DATE: 2026-08-23
SUBJECT: LLM Evaluation Results — Adverse-Action Letter Drafting Assistant

**EXECUTIVE SUMMARY**

We evaluated `gpt-4o-mini`'s ability to draft ECOA/Reg B-compliant adverse-action letters from
loan-officer notes, using a 5-case custom test set targeting completeness, accuracy, tone, bias
risk, and resistance to over-disclosure under pressure. We measured this rather than relying on
public benchmarks because no existing benchmark tests reason-disclosure completeness against
structured source notes, which is the specific compliance requirement at stake here.

**METHODOLOGY**

We rejected three candidate public benchmarks (MMLU, TruthfulQA, BBQ) as insufficient on their
own — see the full benchmark audit — and built a custom 5-prompt mini-benchmark instead,
covering: a single-reason denial, a multi-reason denial (completeness stress test), a paired
fair-lending bias probe, an adversarial appeal that pressures the model to over-disclose
proprietary scoring details, and a Spanish-language letter.

Each generated letter was scored by an LLM-as-judge (`gpt-4o-mini`, temperature 0) following a
structured rubric: extract the source reasons into a checklist, mark each as present/absent/
hallucinated in the letter, assess tone and 8th-grade readability, and combine into a 1-5 score
with structured JSON output (score, reasoning, criteria_met, hallucinated_reasons, missing_
reasons). Rule-based keyword checks supplemented the judge on the completeness and over-
disclosure criteria, since those have unambiguous pass/fail conditions. One model
(`gpt-4o-mini`) was tested as both generator and judge in this pilot round.

**RESULTS**

Live run (see `evaluation_results.json`): all 5 cases scored **5/5** on the judge rubric, with
`completeness`, `accuracy_of_attribution`, and `tone_and_readability` all marked true and zero
hallucinated or missing reasons flagged across the board. Total wall-clock time was ~30 seconds
for all 5 generate+judge pairs; total token usage was 4,385 input / 2,266 output tokens.

A perfect score across all 5 cases on the first live run is itself a caveat, not a clean bill of
health: our test set is small (n=5) and was written by the same person who designed the rubric,
which risks the prompts being "easy" relative to real production inputs (messier loan-officer
notes, ambiguous edge cases, genuinely adversarial customers). It's also consistent with the
verbosity/self-preference judge biases flagged in `evaluation_design.md` — the judge model
(`gpt-4o-mini`) graded the same model's own output, and LLM judges are documented to be lenient
in exactly this configuration. Before trusting this ceiling result, we recommend (1) running the
calibration set described in the judge design (deliberately broken examples that should score
low) to confirm the judge actually discriminates, and (2) expanding the live test set well beyond
5 hand-written cases. The fair-lending paired-comparison (Prompt #3) and Spanish-language (Prompt
#5) cases are flagged as requiring mandatory human sign-off regardless of automated score,
since bias and translation-fidelity findings from an LLM judge are not sufficient evidence on
their own for a compliance conclusion.

**CAVEATS & LIMITATIONS**

This evaluation cannot guarantee regulatory compliance — it is a pre-deployment quality signal,
not a legal certification, and every letter must still be reviewed by a licensed loan officer
before it reaches a customer, per the original design constraint. Results are based on 5 test
cases, which is sufficient to catch obvious failure patterns but not to establish a statistically
reliable error rate; LLM judges also carry documented biases (verbosity preference, self-
preference when judge and generator share a model family — both true in this pilot) that could
inflate or distort scores, and judge output has known run-to-run variance even at temperature 0.
Public-benchmark contamination and saturation concerns (detailed in the benchmark audit) mean we
deliberately did not lean on MMLU/TruthfulQA/BBQ scores as evidence here.

**RECOMMENDATION**

Under these conditions, for this specific letter-drafting task, `gpt-4o-mini` appears usable as a
**first-draft assistant with mandatory human review** — not as an autonomous sender. We have
**low-to-moderate confidence** in this recommendation: a perfect 5/5 score on 5 hand-picked cases
is a promising signal, not proof of production readiness, given the small sample and the
same-model judge/generator setup. Before production sign-off we recommend a larger sample (30-50
cases per denial-reason category, including deliberately messy/edge-case inputs), a judge
calibration pass against known-bad examples to confirm the rubric actually discriminates, and a
dedicated fair-lending audit using the paired-comparison method at scale.

**ADDITIONAL METRICS**

Beyond accuracy: `gpt-4o-mini` is priced at approximately $0.15/1M input tokens and $0.60/1M
output tokens, so even a high-volume rollout (thousands of letters/month) should cost in the
low tens of dollars monthly in model spend — the binding constraint is compliance-reviewer time,
not API cost. Judge-side evaluation cost scales similarly and is cheap enough to run on every
production letter as a pre-send compliance check, not just in periodic audits, which we recommend
as an ongoing safeguard rather than a one-time evaluation.
