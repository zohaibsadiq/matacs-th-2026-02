# Design write-up: AI proposal triage

Zohaib Sadiq · MATACS-TH-2026-02

## The flow in short

The tool has exactly one AI step. Everything else is plain code or a person. The diagram in `diagram/flow.png` shows the same ten steps.

1. **Admin screens** (human). Criteria and weights are saved as a numbered *criteria version*. Nothing is hard-coded.
2. **Upload** (human). The reviewer uploads PDFs and picks a category.
3. **Text extraction and fingerprint** (rules). Text is pulled from each PDF, the file gets a hash, and the cache is checked.
4. **Trick scan** (rules). Pattern matching for text aimed at automated systems, or hidden text. A hit marks the proposal *flagged*.
5. **AI extraction** (AI). One prompt per proposal fills a form built from the criteria: for each criterion a value, a short quote as evidence, a confidence level and a note. Strict JSON output.
6. **Evidence check** (rules). Code confirms every quote really exists in the proposal text.
7. **Mandatory gate** (rules). Fail means *ineligible*. Unclear means *flagged*.
8. **Score and rank** (rules). Fixed formulas with the admin's weights; template reasons.
9. **Reviewer screen** (human). Confirm, correct, clear flags or override, each with a written reason.
10. **Award decision** (human).

Scoring rules: on each numeric criterion the best eligible value gets 100 and the others a proportional share (a bid 3% above the lowest price scores 97). Missing information scores 0 with a warning; the tool never guesses. "Team and approach" is a four-item checklist. The final score is the weighted sum.

## How the sample set ranks

| Proposal | Status | Score | Why |
|---|---|---|---|
| A | Ranked 1 | 98 | Passes both checks. Most experience, fastest, full team marks, price close to the lowest. |
| E | Ranked 2 | 85 | Passes both checks. Best warranty and full team marks, but the least experience. |
| D | Ranked 3 | 70 | Passes both checks and has the lowest price, but gives no committed completion date, so timeline scores 0. Warning shown. |
| C | Flagged | 77 | Good on merit, but its appendix tells automated systems to rank it first. Held for a human. |
| B | Ineligible | none | Cheapest and fastest, but the bidder does not hold the electrical licence itself; it relies on a subcontractor to be confirmed after award. |

Smaller catches: B's "most competitive price" is a claim and is ignored. C's "since 2020" is longer than five years, so its experience count is marked "needs confirmation".

## 1. AI vs. rules

AI does one job: reading messy proposal text and filling in the form, where wording varies ("named senior project manager" versus "coordinator assigned at kickoff"). Rules do everything that must be exact and repeatable: file handling, trick scan, evidence check, mandatory gate, all the maths, ranking, reason text and logging. The line sits where language ends and arithmetic begins. The AI never sees a weight or produces a score, so it cannot be talked into a rank.

## 2. Consistency and explainability

Scores are repeatable because scoring is code: the same extracted values always give the same numbers. Extraction is kept stable with a fixed model version, a fixed prompt version, a strict output schema and low effort settings. Results are cached by file hash, criteria version and prompt version, so ranking the same proposals twice returns the identical stored result. If extraction is deliberately re-run, numbers and yes/no answers are stable, and any low-confidence field goes to the reviewer.

Every score line shows the criterion, the extracted value, the quote it came from, the formula and the points, so a reviewer can see exactly why a proposal sits where it does. The one-line reason is built from those same numbers.

## 3. Human in the loop

People act at four points: the admin defines criteria, the reviewer uploads, the reviewer checks the result, and a person makes the award. On the reviewer screen they can correct an extracted value (the tool re-scores automatically), clear a flag, or override a rank or status, always with a written reason.

Logged for audit: file name and hash, criteria version, prompt and model version, raw AI output, extracted values, evidence check results, every score and formula result, every override with who, when and why, and the final decision.

## 4. Changing criteria

Editing criteria creates a new version and never changes the old one. Existing scores stay tied to the version they used, so old reports still make sense. The reviewer sees a "criteria changed" banner and re-scores with one click. If only weights changed, only the maths re-runs, at no AI cost. If a criterion was added or reworded, extraction re-runs for that criterion only. One ranked list never mixes two versions.

## 5. Risks and safeguards

- **Wrong extraction.** Every value carries a quote and a confidence level. Quotes are checked against the text. Low confidence or missing evidence goes to a human.
- **Made-up facts.** A value without a real quote is marked unverified and cannot pass a mandatory check. Marketing claims are ignored; only concrete numbers and statements are extracted.
- **Bias.** Scoring is arithmetic on stated facts, with the same formula for everyone. Company names could be masked before extraction if needed.
- **Manipulation.** Proposal C is the live example. The trick scan and the AI's own "suspicious text" report both catch it, the prompt treats the document as data, and flagged proposals cannot influence the reference values.
- **Missing or vague information.** Scores 0 with a warning, never a guess (Proposal D's timeline).
- **Cost.** One extraction per file per criteria version, cached. Weight changes cost nothing; the scan uses no AI.
- **Over-trust.** The tool recommends; a person decides, and the log shows how every result was produced.
