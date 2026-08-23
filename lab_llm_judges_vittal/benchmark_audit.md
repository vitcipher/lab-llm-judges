# Benchmark Audit

Scenario: Meridian Community Bank — LLM-drafted adverse-action (loan rejection) letters.
See [00-scenario.md](00-scenario.md) for full context.

Three benchmarks were selected to probe the three failure modes that matter most for this
use case: factual/regulatory accuracy, hallucination/truthfulness, and social-bias risk (fair
lending is a legal requirement, not just a nice-to-have).

---

## Card 1: MMLU (Massive Multitask Language Understanding)

**Year:** 2020 (Hendrycks et al.)
**Source:** "Measuring Massive Multitask Language Understanding," arXiv:2009.03300

**Why it seemed relevant:**
MMLU includes professional/business/law subsets (e.g., "professional_law",
"jurisprudence", "business_ethics") that test whether a model has the underlying factual and
regulatory knowledge needed to reason about compliance obligations like ECOA/Reg B. It's a
natural first check on "does the model know what it's talking about."

**Contamination risk:**
- [x] High - Model definitely saw this during training
- Explanation: MMLU is one of the most widely cited and widely scraped benchmarks on the
  internet. Frontier models (GPT-4-class and later) almost certainly saw MMLU questions and
  discussions of them during pretraining, inflating scores relative to true generalization.

**Saturation risk:**
- [x] High - Many models achieve near-perfect scores
- Explanation: Top models now score in the low-to-mid 90s% on MMLU overall, and the gap between
  models has compressed. It no longer discriminates well between "good enough for this task" and
  "excellent," especially on the general subsets.

**Format:**
- [x] Multiple Choice

**Verdict:**
- [x] Adapt it (explain how)
- How: Don't use MMLU scores as a go/no-go signal. Instead, treat it as a coarse pre-filter —
  a model that does poorly on "professional_law" / "business_ethics" subsets is disqualified
  outright, but a high score says nothing about whether the model can *apply* that knowledge to
  write a compliant, well-reasoned rejection letter in free text. That's what our custom eval
  (Step 3) is for.

---

## Card 2: TruthfulQA

**Year:** 2021 (Lin, Hilton, Evans)
**Source:** "TruthfulQA: Measuring How Models Mimic Human Falsehoods," arXiv:2109.07958

**Why it seemed relevant:**
TruthfulQA measures whether models generate plausible-sounding but false statements —
directly analogous to our top concern: a model inventing a denial reason that sounds
legitimate ("your revolving utilization ratio exceeded 80%") but doesn't match what the loan
officer's notes actually said.

**Contamination risk:**
- [x] Medium - Some overlap possible
- Explanation: TruthfulQA is public and widely discussed, so some question/answer pairs have
  likely leaked into training data. However, its adversarial framing (questions designed to
  elicit common misconceptions) means memorizing the dataset doesn't fully solve the underlying
  problem the way it might for a knowledge-recall benchmark.

**Saturation risk:**
- [x] Medium - Some models perform well
- Explanation: Scores vary widely by model family and are still meaningfully below ceiling for
  many open models, though top proprietary models now score well. It still discriminates,
  but is trending toward saturation for frontier models.

**Format:**
- [x] Free-form text (also has a multiple-choice variant, MC1/MC2)

**Verdict:**
- [x] Reject it (explain why)
- Why: TruthfulQA targets *general* factual misconceptions (trivia, folk wisdom, conspiracy
  theories) — none of its question categories map to our actual failure surface, which is
  "does the letter's stated reason match the structured input data." It would burn eval budget
  measuring the wrong kind of truthfulness. We're better off building a custom rule-based check
  that diffs the letter's stated reasons against the loan officer's input notes (see Step 3,
  Prompt #2), which directly measures what we care about instead of a proxy.

---

## Card 3: BBQ (Bias Benchmark for QA)

**Year:** 2022 (Parrish, Chen, Nangia, Padmakumar, Phang, Thompson, Htut, Bowman)
**Source:** "BBQ: A Hand-Built Bias Benchmark for Question Answering," arXiv:2110.08193

**Why it seemed relevant:**
BBQ tests whether models rely on social biases/stereotypes (age, race, gender, nationality,
disability, etc.) when answering ambiguous questions. Fair lending law (ECOA, Fair Housing Act)
makes this a legal requirement, not just an ethics concern — a rejection letter that implicitly
correlates a denial reason with a protected characteristic is a real regulatory and reputational
risk.

**Contamination risk:**
- [x] Low - Model likely not trained on this data
- Explanation: BBQ's item bank is deliberately hand-constructed and templated to avoid overlap
  with common pretraining corpora, and it is less frequently cited/reproduced in blog posts and
  leaderboards than MMLU, so direct memorization is less likely.

**Saturation risk:**
- [x] Low - Benchmark is challenging
- Explanation: Bias scores (accuracy in ambiguous contexts, and bias score in disambiguated
  contexts) still show meaningful gaps across models, and "ambiguous context" performance in
  particular remains far from ceiling for most models.

**Format:**
- [x] Multiple Choice

**Verdict:**
- [x] Adapt it (explain how)
- How: BBQ's question format (short scenario + ambiguous question) doesn't match our free-text
  letter-generation task, but its *methodology* is directly reusable: construct paired test
  cases where the applicant's demographic-adjacent details (name, zip code, employer type) are
  swapped while the underlying financial facts stay identical, and check whether the generated
  letter's content or tone changes. This becomes an audit tool we run periodically on our own
  custom eval set rather than a benchmark we report a single score from.

---

## Summary

None of the three benchmarks can be used as-is to certify this use case. MMLU is a coarse
knowledge pre-filter, TruthfulQA doesn't target our specific truthfulness failure mode, and BBQ's
*methodology* (not its content) is reusable as a fairness audit technique. This is the core
justification for building the custom 5-prompt mini-benchmark in Step 3.
