# Reflection

## Question 1: What would change if the client's data was in French?

Two layers of the evaluation would need rework: the benchmarks and the judge itself. On the
benchmark side, MMLU/TruthfulQA/BBQ are all English-first (BBQ especially — its stereotype
templates are built around US social categories that don't map cleanly onto French social
context), so I'd look for French-native equivalents (e.g., FQuAD or French subsets of
multilingual suites) rather than assuming translated English benchmarks transfer meaning
correctly. On the judge side, the harder problem is that "is this tone appropriate" and "is this
compliant with local consumer-protection law" are not just translation problems — French
consumer credit law (Code de la consommation) has its own adverse-action disclosure requirements
that don't map one-to-one onto ECOA/Reg B, so the ground-truth checklist itself needs to be
rebuilt with a French regulatory expert, not just translated. New challenges would include:
verifying the LLM judge is actually fluent enough in French to catch subtle tone or accuracy
errors (it's easy to assume a model that speaks French is judging French as well as it judges
English — this needs to be tested explicitly, the same way we flagged Prompt #5), and
formality/register issues (French has tu/vous distinctions with real social-appropriateness
stakes that don't exist in English at all). Quality verification would need a native French
speaker with financial-services domain knowledge in the loop, at least until the judge is proven
reliable — I would not trust an English-calibrated judge's French scores without a calibration
pass using French reference examples.

## Question 2: "Is this model AGI-level?"

I'd push back on the framing directly: "AGI-level" isn't a criterion any evaluation — ours or a
public benchmark — can actually answer, because it's not a well-defined, measurable target. It's
a marketing/discourse term, not a technical specification with agreed pass/fail conditions the
way "95% accuracy on this compliance checklist" is. What I *can* answer is much narrower and much
more useful to Meridian: does this model reliably draft compliant, well-toned adverse-action
letters across the failure modes we tested, and how does it compare to alternatives on that exact
task? Answering the literal AGI question would require evaluating general reasoning, transfer to
entirely novel domains, autonomous multi-step planning, and calibrated uncertainty across a vastly
broader task distribution than anything in scope here — and even the AI research community
doesn't agree on what battery of tests would settle the question, let alone have run it
conclusively on any current model. My caveat to the client would be: judge this model on whether
it does *your* job well, not on a label that isn't operationally defined — and be skeptical of any
vendor claiming otherwise as a data point in a purchase decision.

## Question 3: What is the one thing that requires a human?

The fair-lending bias judgment in Prompt #3 is the clearest case. An LLM-as-judge can flag
*surface-level* divergence between the paired letters (different word count, different reasons
cited, obviously different tone) — that part is mechanically checkable. But determining whether a
subtle difference constitutes unlawful disparate treatment under fair-lending law is a legal
judgment with real consequences (regulatory exposure, litigation risk), and it requires
weighing context, intent, and legal precedent in a way no automated method — rule-based or
LLM-judge — is authorized or reliable enough to make alone. The LLM judge is also the wrong tool
here for a structural reason, not just a risk-tolerance one: it was trained on the same kind of
biased data that produces the disparities it would be asked to detect, so it can share the blind
spots it's supposed to catch. In practice, I'd use the LLM judge as a triage/flagging layer that
surfaces candidate divergences at scale (since a human can't manually review every paired
comparison), then route anything flagged — plus a random unflagged sample, to catch what the
judge misses — to a human fair-lending compliance reviewer for the actual determination. The
automation's job is recall (don't miss cases), and the human's job is precision and legal
accountability (get the final call right).
