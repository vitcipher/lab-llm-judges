# Client Scenario

**Client:** Meridian Community Bank (fictional, mid-size regional bank, ~40 branches)

**Goal:** Meridian wants to use an LLM to draft first-pass adverse-action (rejection) letters for
personal loan applications. A human loan officer reviews and approves every letter before it is
sent — the model is a drafting assistant, not an autonomous decision-maker.

**Key requirements:**
- Every letter must cite the *specific, accurate* reasons for denial, matching the loan officer's
  input notes (required under the Equal Credit Opportunity Act / Regulation B "adverse action
  notice" rules — vague reasons like "poor application" are not compliant).
- Tone must be clear, professional, and empathetic — this is often the worst news a customer
  receives from their bank that year.
- Must not promise outcomes the bank can't guarantee (e.g., "you will be approved if you reapply
  in 6 months").
- Must not disclose proprietary credit-scoring model internals, even under direct customer
  pressure.
- Must be written at roughly an 8th-grade reading level (plain-language compliance expectation).

**Main concerns / failure modes:**
- **Hallucination:** inventing a denial reason not present in the loan officer's notes, or
  omitting a required reason (incomplete adverse-action notice = compliance violation).
- **Tone failure:** letters that read as cold, robotic, or legally accurate but hostile.
- **Discriminatory language:** phrasing that correlates denial reasons with protected classes
  (race, national origin, age, etc.) even indirectly — a fair-lending risk.
- **Over-disclosure:** revealing internal scoring model details when a customer appeals or asks
  "why exactly was I scored this way?"
