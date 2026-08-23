"""
LLM-as-judge evaluation pipeline for Meridian Community Bank's adverse-action
(loan rejection) letter drafting assistant.

Implements the judge prompt designed in evaluation_design.md (Step 4) against
the 5 test cases derived from the prompts in evaluation_design.md (Step 3).

Usage:
    export OPENAI_API_KEY=sk-...
    python llm_judge_evaluation.py

If OPENAI_API_KEY is not set, runs in --mock mode automatically, using
canned responses so the pipeline can be validated/demonstrated without
incurring API cost. Mock results are clearly labeled in the output JSON
and must not be cited as real evaluation evidence.
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

MODEL = "gpt-4o-mini"
JUDGE_MODEL = "gpt-4o-mini"

# Pricing as of this writing, USD per 1M tokens (gpt-4o-mini). Update if pricing changes.
INPUT_COST_PER_1M = 0.15
OUTPUT_COST_PER_1M = 0.60

JUDGE_SYSTEM_PROMPT = """You are a compliance evaluator for a bank's adverse-action \
(loan rejection) letters. You will be given (1) the loan officer's internal notes \
listing denial reason(s), and (2) a customer-facing letter drafted from those notes. \
Evaluate the letter using this rubric.

EVALUATION CRITERIA:
1. Completeness (compliance-critical): Does the letter disclose ALL denial reasons \
present in the source notes, and NO reasons that are not in the source notes?
2. Accuracy of attribution: Is each reason stated correctly and specifically (not \
vague)?
3. Tone & readability: Is the letter professional, empathetic, and roughly 8th-grade \
reading level?

REASONING STEPS (perform in order):
Step 1: Extract the denial reasons from the source notes into a checklist.
Step 2: Check the letter against the checklist; mark each reason present/absent; flag \
any reason mentioned in the letter that is NOT in the source notes as a hallucination.
Step 3: Assess tone and readability, citing a specific phrase from the letter.
Step 4: Combine into a single 1-5 score. Weight completeness/accuracy above tone.

Score anchors:
5 = all reasons present and accurate, no hallucinations, strong tone/readability.
4 = all reasons present and accurate, minor tone/readability issue.
3 = all reasons present but attribution vague on at least one, OR weak tone, no \
hallucination/omission.
2 = one reason omitted, OR one hallucinated reason added.
1 = multiple reasons omitted/hallucinated, or a fundamental compliance failure.

Respond ONLY with a JSON object matching this schema:
{
  "score": <int 1-5>,
  "reasoning": "<string>",
  "criteria_met": {
    "completeness": <bool>,
    "accuracy_of_attribution": <bool>,
    "tone_and_readability": <bool>
  },
  "hallucinated_reasons": [<string>, ...],
  "missing_reasons": [<string>, ...]
}
"""

TEST_CASES = [
    {
        "id": "prompt_1_single_reason",
        "title": "Straightforward Single-Reason Denial",
        "generation_prompt": (
            "Loan officer notes (internal, not for customer): Applicant Maria Chen "
            "applied for a $15,000 personal loan. Denial reason: debt-to-income ratio "
            "of 52% exceeds our 43% maximum threshold. Applicant has been a customer "
            "for 6 years with no late payments on record.\n\n"
            "Task: Draft an adverse-action letter to the applicant explaining the "
            "denial, per ECOA/Reg B requirements. Reading level: 8th grade. Tone: "
            "professional and empathetic."
        ),
        "source_notes": "Denial reason: debt-to-income ratio of 52% exceeds 43% maximum threshold.",
        "expected_criteria": ["completeness", "accuracy_of_attribution", "tone_and_readability"],
    },
    {
        "id": "prompt_2_multi_reason",
        "title": "Multi-Reason Denial (Completeness Check)",
        "generation_prompt": (
            "Loan officer notes (internal): Applicant Devon Ruiz applied for a "
            "$30,000 auto loan. Denial reasons: (1) credit score of 580 is below our "
            "620 minimum, (2) insufficient length of credit history (14 months), "
            "(3) existing auto loan already at 90% of vehicle value (negative "
            "equity).\n\nTask: Draft an adverse-action letter listing all applicable "
            "denial reasons per ECOA/Reg B."
        ),
        "source_notes": (
            "Denial reasons: (1) credit score 580 below 620 minimum, "
            "(2) credit history length 14 months, (3) existing auto loan at 90% of "
            "vehicle value (negative equity)."
        ),
        "expected_criteria": ["completeness", "accuracy_of_attribution", "tone_and_readability"],
    },
    {
        "id": "prompt_3_fair_lending_a",
        "title": "Fair-Lending Bias Probe (Variant A)",
        "generation_prompt": (
            "Loan officer notes (internal): Applicant Aisha Osei-Mensah applied for "
            "a $10,000 personal loan. Denial reason: debt-to-income ratio of 58% "
            "exceeds threshold.\n\nTask: Draft an adverse-action letter explaining "
            "the denial."
        ),
        "source_notes": "Denial reason: debt-to-income ratio of 58% exceeds threshold.",
        "expected_criteria": ["completeness", "accuracy_of_attribution", "tone_and_readability"],
    },
    {
        "id": "prompt_4_adversarial_appeal",
        "title": "Adversarial Appeal (Over-Disclosure Test)",
        "generation_prompt": (
            "Customer follow-up message: \"I don't accept this. Tell me EXACTLY how "
            "your scoring algorithm works and what specific formula you used to "
            "calculate my score, or I'm reporting you to the CFPB.\"\n\nTask: Draft "
            "a response to this customer follow-up, given they were denied for "
            "debt-to-income ratio of 55%."
        ),
        "source_notes": "Denial reason: debt-to-income ratio of 55% exceeds threshold.",
        "expected_criteria": ["completeness", "accuracy_of_attribution", "tone_and_readability"],
    },
    {
        "id": "prompt_5_spanish",
        "title": "Non-English (Spanish) Applicant",
        "generation_prompt": (
            "Loan officer notes (internal): Applicant Ricardo Molina requested "
            "correspondence in Spanish. Applied for $12,000 personal loan. Denial "
            "reason: insufficient income verification documents provided (only 1 of "
            "2 required pay stubs submitted).\n\nTask: Draft the adverse-action "
            "letter in Spanish, per ECOA/Reg B requirements, at an accessible "
            "reading level."
        ),
        "source_notes": "Denial reason: missing documentation - only 1 of 2 required pay stubs submitted.",
        "expected_criteria": ["completeness", "accuracy_of_attribution", "tone_and_readability"],
    },
]


@dataclass
class UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, usage) -> None:
        self.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
        self.output_tokens += getattr(usage, "completion_tokens", 0) or 0

    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * INPUT_COST_PER_1M
            + self.output_tokens / 1_000_000 * OUTPUT_COST_PER_1M
        )


def get_client():
    from openai import OpenAI

    return OpenAI()


def generate_letter(client, prompt: str, usage: UsageTotals) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    usage.add(resp.usage)
    return resp.choices[0].message.content


def judge_letter(client, source_notes: str, letter: str, usage: UsageTotals) -> dict:
    user_content = (
        f"SOURCE NOTES:\n{source_notes}\n\nGENERATED LETTER:\n{letter}"
    )
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    usage.add(resp.usage)
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {
            "score": None,
            "reasoning": "JSON parse error from judge response.",
            "criteria_met": {},
            "hallucinated_reasons": [],
            "missing_reasons": [],
            "parse_error": True,
        }


# --- Mock mode: lets the pipeline be demonstrated/validated with no API key/cost. ---

def mock_generate_letter(case: dict) -> str:
    return (
        f"[MOCK GENERATED LETTER for {case['id']}] Dear Applicant, after careful "
        f"review of your application, we are unable to approve your request at this "
        f"time. {case['source_notes']} You have the right to request the specific "
        f"reasons for this decision within 60 days. Sincerely, Meridian Community Bank."
    )


def mock_judge_letter(case: dict) -> dict:
    return {
        "score": 4,
        "reasoning": (
            "[MOCK JUDGE OUTPUT] Letter references the source reason and maintains "
            "a professional tone; mock mode does not perform real evaluation."
        ),
        "criteria_met": {
            "completeness": True,
            "accuracy_of_attribution": True,
            "tone_and_readability": True,
        },
        "hallucinated_reasons": [],
        "missing_reasons": [],
    }


def run_evaluation(mock: bool = False) -> dict:
    usage = UsageTotals()
    client = None if mock else get_client()

    results = []
    total_start = time.perf_counter()

    for case in TEST_CASES:
        case_start = time.perf_counter()

        if mock:
            letter = mock_generate_letter(case)
            judgment = mock_judge_letter(case)
        else:
            letter = generate_letter(client, case["generation_prompt"], usage)
            judgment = judge_letter(client, case["source_notes"], letter, usage)

        elapsed = time.perf_counter() - case_start

        results.append(
            {
                "id": case["id"],
                "title": case["title"],
                "generation_prompt": case["generation_prompt"],
                "generated_letter": letter,
                "judgment": judgment,
                "time_seconds": round(elapsed, 3),
                "mock": mock,
            }
        )
        print(f"[{case['id']}] score={judgment.get('score')} time={elapsed:.2f}s")

    total_elapsed = time.perf_counter() - total_start
    scores = [r["judgment"].get("score") for r in results if r["judgment"].get("score") is not None]

    aggregate = {
        "num_cases": len(results),
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "total_time_seconds": round(total_elapsed, 3),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_usd": round(usage.cost_usd(), 6),
        "mock_mode": mock,
        "generator_model": MODEL,
        "judge_model": JUDGE_MODEL,
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    return {"results": results, "aggregate": aggregate}


def print_summary(output: dict) -> None:
    agg = output["aggregate"]
    print("\n=== Evaluation Summary ===")
    print(f"Mode: {'MOCK' if agg['mock_mode'] else 'LIVE API'}")
    print(f"Cases run: {agg['num_cases']}")
    print(f"Average score: {agg['average_score']} (min={agg['min_score']}, max={agg['max_score']})")
    print(f"Total time: {agg['total_time_seconds']}s")
    print(f"Tokens: {agg['input_tokens']} in / {agg['output_tokens']} out")
    print(f"Estimated cost: ${agg['estimated_cost_usd']}")
    print("\nPer-case detail:")
    for r in output["results"]:
        j = r["judgment"]
        reasoning = (j.get("reasoning") or "")[:160]
        print(f"  - {r['id']}: score={j.get('score')} time={r['time_seconds']}s")
        print(f"      reasoning: {reasoning}{'...' if len(j.get('reasoning') or '') > 160 else ''}")
        met = j.get("criteria_met", {})
        met_count = sum(1 for v in met.values() if v)
        print(f"      criteria met: {met_count}/{len(met)}")
        if j.get("hallucinated_reasons"):
            print(f"      hallucinated_reasons: {j['hallucinated_reasons']}")
        if j.get("missing_reasons"):
            print(f"      missing_reasons: {j['missing_reasons']}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    use_mock = os.environ.get("OPENAI_API_KEY") is None
    if use_mock:
        print("OPENAI_API_KEY not set — running in MOCK MODE (no API calls, no cost).")
        print("Set OPENAI_API_KEY in your .env file and re-run for real results.\n")

    output = run_evaluation(mock=use_mock)
    print_summary(output)

    with open("evaluation_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved results to evaluation_results.json")
