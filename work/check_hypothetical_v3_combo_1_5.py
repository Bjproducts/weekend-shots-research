from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "outputs" / "hypothetical_v3_combo_1_5" / "results.json"

data = json.loads(RESULT.read_text(encoding="utf-8"))
checks = {
    "scenario_is_not_price_evidence": data["status"] == "complete_hypothetical_not_price_evidence",
    "prospective_gate_disabled": data["spec"]["prospective_gate_eligible"] is False,
    "profit_claim_disabled": data["spec"]["profit_claim_permitted"] is False,
    "assumed_price_is_1_5": data["spec"]["assumed_decimal_price_per_leg"] == 1.5,
    "source_reconciles": data["source_official_picks"] == 23 and data["source_hits_3plus"] == 20,
    "every_source_pick_accounted_for": sum(len(row["legs"]) for row in data["tickets"]) + len(data["no_combo"]) == data["source_official_picks"],
    "minimum_two_legs": all(len(row["legs"]) >= 2 for row in data["tickets"]),
    "maximum_three_legs": all(len(row["legs"]) <= 3 for row in data["tickets"]),
    "one_per_league": all(len({leg["league"] for leg in row["legs"]}) == len(row["legs"]) for row in data["tickets"]),
    "no_duplicate_selections": len({leg["selection_id"] for row in data["tickets"] for leg in row["legs"]}) == sum(len(row["legs"]) for row in data["tickets"]),
    "derived_prices_reconcile": all(abs(row["derived_assumed_odds"] - 1.5 ** len(row["legs"])) < 1e-9 for row in data["tickets"]),
    "stake_is_90_percent": all(abs(row["stake"] - round(row["bankroll_snapshot"] * 0.9, 2)) < 1e-9 for row in data["tickets"]),
    "headline_ticket_count": data["hypothetical_tickets"] == 1,
    "headline_ticket_wins": data["winning_tickets"] == 1,
    "headline_ending_bankroll": data["bankroll"]["ending_bankroll"] == 212.5,
}
failures = [name for name, passed in checks.items() if not passed]
print(json.dumps({"passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}, indent=2))
raise SystemExit(1 if failures else 0)
