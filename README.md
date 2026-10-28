# MATACS-TH-2026-02: AI Proposal Triage Design

| | |
|---|---|
| **Name** | Zohaib Sadiq |
| **Reference** | MATACS-TH-2026-02 |
| **Time spent** | About 50 minutes |

## Files in this repository

- [WRITEUP.md](WRITEUP.md): the design, the sample ranking, and answers to the five questions
- [diagram/flow.png](diagram/flow.png): process flow from upload to ranked output, showing AI steps, rule steps and human checkpoints
- [PROMPTS.md](PROMPTS.md): the exact extraction prompt and output schema
- [ranking.json](ranking.json): expected ranking of proposals A to E
- [prototype/](prototype/) (optional): a small script that runs the prompt and the scoring rules
  - [prototype/run_triage.py](prototype/run_triage.py): the pipeline
  - [prototype/scoring.py](prototype/scoring.py): the rules (gate, scoring, ranking, reasons)
  - [prototype/criteria.json](prototype/criteria.json): what the admin screens would save
  - [prototype/fixtures/extracted_demo.json](prototype/fixtures/extracted_demo.json): hand-checked values so the rules run without an API key
  - [prototype/.env.example](prototype/.env.example): key goes in `.env`, which is git-ignored
  - [prototype/requirements.txt](prototype/requirements.txt): the two Python packages needed for live mode
  - [prototype/samples/README.md](prototype/samples/README.md): where proposal text goes locally, never in git
  - [prototype/README.md](prototype/README.md): how to run it

## The design in three lines

1. **AI does one job.** It reads each proposal and fills in a form built from the admin's criteria: a value, a quote as evidence, a confidence level and a note per criterion.
2. **Plain code does the rest.** Trick scan, evidence check, mandatory gate, scoring with the admin's weights, ranking, one-line reasons, audit log.
3. **A person decides.** The reviewer can correct, clear a flag or override with a reason. A human makes the award.

## Expected result for the sample set

| Rank | Proposal | Status | Score | In one line |
|---|---|---|---|---|
| 1 | A | ranked | 98 | Strong on every criterion |
| 2 | E | ranked | 85 | Best warranty, least experience |
| 3 | D | ranked | 70 | Lowest price, but no committed timeline |
| - | C | flagged | 77 | Hidden instruction aimed at automated reviewers; needs a human |
| - | B | ineligible | - | Bidder does not hold the electrical licence itself |

Run `python run_triage.py --dry-run --check ../ranking.json` in the prototype folder to reproduce this.

## How I used AI tools

I used Claude Code (Anthropic's Claude) as a drafting partner: it summarised the brief, proposed the process flow and the scoring rules, drafted the write-up, prompt and diagram, and wrote and tested the prototype script, which I reviewed and accepted without overriding its design choices. The correction along the way was one the AI made to its own first draft during that review: its first answer on consistency relied on a "temperature zero" setting that the current API no longer accepts, so it was replaced with a strict output schema, low effort and caching by file hash. I did not find a point where I disagreed with the final design, so I have not claimed one.

## Notes

- No proposal text is included in this repository. Proposals are referred to by letter only, as the brief asks.
- No API keys are committed. Copy `prototype/.env.example` to `prototype/.env` to run the live prototype.
- Assumptions: the two mandatory criteria are strict pass/fail as written by the admin, so a licence held only by a subcontractor "to be confirmed later" is a fail. A proposal with no committed timeline is still ranked, with 0 points on that criterion and a visible warning, rather than being excluded.
