"""
scoring.py - the RULES half of the triage tool.

Everything in this file is plain, deterministic code. Given the same extracted
values and the same criteria set, it always produces the same scores, ranks and
reasons. No AI is used here.

Input shape (one entry per proposal letter):
    {
      "fields": {
        "<criterion id>": {"value": ..., "evidence": "...", "confidence": "high|medium|low",
                           "note": "...", "verified": true|false|null}
      },
      "suspicious_text": ["..."],      # anything the AI saw that was aimed at the reviewer/system
      "scan_hits": ["..."]             # anything the rule-based pattern scan found
    }
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Step 7: mandatory gate
# ---------------------------------------------------------------------------

def mandatory_gate(extraction: dict, criteria: dict) -> tuple[str, list[str]]:
    """Return ("pass" | "fail" | "unclear", reasons)."""
    reasons: list[str] = []
    outcome = "pass"
    for crit in criteria["criteria"]:
        if crit["type"] != "mandatory":
            continue
        field = extraction["fields"].get(crit["id"], {})
        value = field.get("value")
        note = field.get("note") or ""
        if value is False:
            outcome = "fail"
            reasons.append(f"Fails mandatory check '{crit['name']}'" + (f": {note}" if note else ""))
        elif value is None or field.get("verified") is False:
            if outcome != "fail":
                outcome = "unclear"
            reasons.append(f"Mandatory check '{crit['name']}' could not be confirmed from the text")
    return outcome, reasons


# ---------------------------------------------------------------------------
# Step 8: scoring helpers
# ---------------------------------------------------------------------------

def _ratio(value, best, direction: str) -> float:
    """Best eligible value scores 100; others get a proportional share (capped at 100)."""
    if value is None or best is None or best == 0 or value == 0:
        return 0.0
    if direction == "lower_is_better":
        return min(100.0, best / value * 100.0)
    return min(100.0, value / best * 100.0)


def _best(values: list, direction: str):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return min(values) if direction == "lower_is_better" else max(values)


def _number_parts(crit: dict) -> list[str]:
    if crit["extract"]["kind"] == "number_set":
        return [p["id"] for p in crit["extract"]["parts"]]
    return []


def score_criterion(crit: dict, field: dict, reference: dict) -> tuple[float, list[str]]:
    """Score one weighted criterion for one proposal. Returns (points 0-100, warnings)."""
    warnings: list[str] = []
    value = field.get("value")
    scoring = crit["scoring"]
    kind = crit["extract"]["kind"]

    if kind == "checklist":
        items = crit["extract"]["items"]
        answers = value if isinstance(value, dict) else {}
        got = [i["id"] for i in items if answers.get(i["id"]) is True]
        missing = [i["id"] for i in items if answers.get(i["id"]) is not True]
        if missing:
            warnings.append(f"{crit['name']}: not shown - {', '.join(missing)}")
        return 100.0 * len(got) / len(items), warnings

    if kind == "number_set":
        parts = _number_parts(crit)
        answers = value if isinstance(value, dict) else {}
        part_scores = []
        for part in parts:
            v = answers.get(part)
            if v is None:
                warnings.append(f"{crit['name']}: no {part.replace('_', ' ')} stated")
                part_scores.append(0.0)
            else:
                part_scores.append(_ratio(v, reference.get((crit["id"], part)), scoring["direction"]))
        return sum(part_scores) / len(parts), warnings

    # plain number
    if value is None:
        warnings.append(f"{crit['name']}: not stated in the proposal (scores 0)")
        return 0.0, warnings
    limit = scoring.get("limit")
    if limit is not None and scoring["direction"] == "lower_is_better" and value > limit:
        warnings.append(f"{crit['name']}: {value} is over the limit of {limit} (scores 0)")
        return 0.0, warnings
    return _ratio(value, reference.get((crit["id"], None)), scoring["direction"]), warnings


def build_reference(extractions: dict[str, dict], criteria: dict, reference_letters: list[str]) -> dict:
    """
    "Best in set" values, taken ONLY from proposals that passed the gate and carry no flags.
    Flagged proposals are scored against this reference but never influence it, so a
    manipulated bid cannot drag other bidders' scores down.
    """
    ref: dict = {}
    for crit in criteria["criteria"]:
        if crit["type"] != "weighted" or crit["scoring"]["method"] != "ratio":
            continue
        direction = crit["scoring"]["direction"]
        limit = crit["scoring"].get("limit")
        parts = _number_parts(crit) or [None]
        for part in parts:
            values = []
            for letter in reference_letters:
                v = extractions[letter]["fields"].get(crit["id"], {}).get("value")
                if part is not None:
                    v = v.get(part) if isinstance(v, dict) else None
                if v is None:
                    continue
                if limit is not None and direction == "lower_is_better" and v > limit:
                    continue
                values.append(v)
            ref[(crit["id"], part)] = _best(values, direction)
    return ref


# ---------------------------------------------------------------------------
# Step 8: evaluate the whole set
# ---------------------------------------------------------------------------

def evaluate(extractions: dict[str, dict], criteria: dict) -> list[dict]:
    """Gate, score, rank and explain every proposal. Pure function."""
    letters = sorted(extractions)
    results: dict[str, dict] = {}

    # 1. gate + flags
    for letter in letters:
        ex = extractions[letter]
        gate, gate_reasons = mandatory_gate(ex, criteria)
        flags = list(gate_reasons) if gate == "unclear" else []
        if ex.get("scan_hits"):
            flags.append("Pattern scan found text aimed at automated systems: " + "; ".join(ex["scan_hits"]))
        if ex.get("suspicious_text"):
            flags.append("AI extractor reported text addressed to the reviewer/system: " + "; ".join(ex["suspicious_text"]))
        unverified = [cid for cid, f in ex["fields"].items() if f.get("verified") is False]
        if unverified:
            flags.append("Evidence quote not found in the proposal text for: " + ", ".join(unverified))

        if gate == "fail":
            status = "ineligible"
        elif flags:
            status = "flagged"
        else:
            status = "ranked"
        results[letter] = {
            "proposal": letter, "status": status, "gate": gate,
            "gate_reasons": gate_reasons, "flags": flags,
            "rank": None, "score": None, "breakdown": {}, "warnings": [], "reason": "",
        }

    # 2. reference values come only from clean, ranked proposals
    reference_letters = [l for l in letters if results[l]["status"] == "ranked"]
    reference = build_reference(extractions, criteria, reference_letters)

    # 3. score every proposal whose gate passed (ranked, or flagged-but-passing)
    for letter in letters:
        res = results[letter]
        if res["gate"] != "pass":
            continue
        total = 0.0
        for crit in criteria["criteria"]:
            if crit["type"] != "weighted":
                continue
            field = extractions[letter]["fields"].get(crit["id"], {})
            points, warnings = score_criterion(crit, field, reference)
            weighted = points * crit["weight"] / 100.0
            total += weighted
            res["warnings"].extend(warnings)
            res["breakdown"][crit["id"]] = {
                "name": crit["name"], "weight": crit["weight"], "value": field.get("value"),
                "points": round(points, 1), "weighted": round(weighted, 2),
                "evidence": field.get("evidence", ""), "confidence": field.get("confidence", ""),
                "note": field.get("note", ""),
            }
        res["score"] = round(total)

    # 4. rank only the clean ones (score desc, then letter for a deterministic tie-break)
    ranked = sorted(reference_letters, key=lambda l: (-results[l]["score"], l))
    for i, letter in enumerate(ranked, start=1):
        results[letter]["rank"] = i

    # 5. reasons
    for letter in letters:
        results[letter]["reason"] = build_reason(results[letter])

    order = {"ranked": 0, "flagged": 1, "ineligible": 2}
    return sorted(results.values(), key=lambda r: (order[r["status"]], r["rank"] or 99, r["proposal"]))


def build_reason(res: dict) -> str:
    """One plain-English line built from the numbers (a template, not AI)."""
    if res["status"] == "ineligible":
        return "; ".join(res["gate_reasons"]) + "."
    if res["status"] == "flagged" and res["score"] is None:
        return "Held for human review: " + "; ".join(res["flags"]) + "."
    bd = res["breakdown"]
    full = [v["name"].lower() for v in bd.values() if v["points"] >= 99.5]
    weakest = min(bd.values(), key=lambda v: v["points"])
    parts = ["Passes both mandatory checks"]
    if full:
        parts.append("full marks on " + ", ".join(full))
    parts.append(f"weakest on {weakest['name'].lower()} ({weakest['points']:.0f}/100)")
    text = "; ".join(parts)
    if res["warnings"]:
        text += ". Warning: " + "; ".join(res["warnings"])
    if res["status"] == "flagged":
        text = (f"Would score {res['score']} on merit, but held for human review: "
                + "; ".join(res["flags"]) + ". " + text)
    return text + "."


def to_ranking_json(results: list[dict]) -> list[dict]:
    """The exact shape the brief asks for in ranking.json."""
    return [
        {"proposal": r["proposal"], "rank": r["rank"], "status": r["status"],
         "score": r["score"], "reason": r["reason"]}
        for r in results
    ]
