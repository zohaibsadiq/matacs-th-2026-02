# Prototype

A small script that runs the design end to end on the five sample proposals.
Extra credit only; no deployment needed.

| File | What it is |
|---|---|
| `criteria.json` | What the admin screens would save: the category, mandatory and weighted criteria, weights and scoring method. Nothing is hard-coded in the script. |
| `run_triage.py` | The pipeline: read text, fingerprint and cache, trick scan, AI extraction (the only AI step), evidence check, then hand over to the rules. |
| `scoring.py` | The rules: mandatory gate, scoring formulas, ranking, template reasons. Pure functions, no AI. |
| `fixtures/extracted_demo.json` | Hand-checked extraction values for A to E, so the rules can run without an API key. |
| `samples/` | Where the proposal text files go locally. They are git-ignored on purpose. |
| `.env.example` | Copy to `.env` and add your key. `.env` is git-ignored. |

## Run it

```bash
cd prototype
pip install -r requirements.txt

# 1. No API key needed - demonstrates the rules and reproduces ranking.json
python run_triage.py --dry-run --check ../ranking.json

# 2. Live - calls Claude once per proposal (see samples/README.md first)
# copy .env.example to .env and put your key in it (Windows: copy .env.example .env)
python run_triage.py --check ../ranking.json --out output/run.json

# 3. Print the exact prompt and JSON schema that are sent
python run_triage.py --show-prompt
```

## What to look at

- The model is asked for a **value, a quote, a confidence level and a note** per criterion, in a strict JSON schema built from `criteria.json`.
- `verify_evidence` checks every quote against the proposal text. A value without a real quote is marked unverified.
- `trick_scan` is the rule-based first line against text aimed at automated systems; the model also reports such text in `suspicious_text`. Either one flags the proposal.
- `scoring.build_reference` takes "best in set" values only from clean, ranked proposals, so a flagged bid cannot pull other scores down.
- Results are cached in `.cache/` by file hash + criteria version + prompt version + model, so a re-run returns the identical stored result.
- `--out` writes a run record (audit) with the model, prompt version, criteria version, file hashes, raw AI output and every score.
