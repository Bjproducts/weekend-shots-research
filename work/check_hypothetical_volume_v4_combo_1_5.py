"""Reconcile the retrospective assumed-price volume-v4 mechanics report."""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs/hypothetical_volume_v4_combo_1_5/results.json"


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert data["spec"]["prospective_gate_eligible"] is False
    assert data["spec"]["price_source"] == "assumed_not_observed"
    assert data["source_official_picks"] == data["no_combo_selections"] + sum(
        len(row["legs"]) for row in data["tracks"]["fixed_10"]["tickets"]
    )
    fixed_ids = []
    for track, result in data["tracks"].items():
        assert result["staking_track"] == track
        for ticket in result["tickets"]:
            assert 2 <= len(ticket["legs"]) <= 3
            assert len({leg["fixture"] for leg in ticket["legs"]}) == len(ticket["legs"])
            league_counts = {league: sum(leg["league"] == league for leg in ticket["legs"]) for league in {leg["league"] for leg in ticket["legs"]}}
            assert max(league_counts.values()) <= 2
            assert math.isclose(ticket["derived_assumed_odds"], 1.5 ** len(ticket["legs"]))
            assert math.isclose(ticket["stake"], round(ticket["bankroll_snapshot"] * result["stake_fraction"], 2))
            if track == "fixed_10":
                fixed_ids.extend(leg["selection_id"] for leg in ticket["legs"])
    assert len(fixed_ids) == len(set(fixed_ids))
    assert data["tracks"]["fixed_10"]["stake_fraction"] == 0.1
    assert data["tracks"]["stress_90"]["stake_fraction"] == 0.9
    assert data["tracks"]["full_rollover_100"]["stake_fraction"] == 1.0
    rollover = data["tracks"]["full_rollover_100"]
    assert rollover["rollover_formula"] == data["spec"]["full_rollover_formula"]
    if rollover["tickets"]:
        first = rollover["tickets"][0]
        expected = round(100 * 1.5 ** len(first["legs"]), 2) if first["result"] == "win" else 0.0
        assert first["bankroll_after_settlement"] == expected
    print(json.dumps({"status": "ok", "source_legs": data["source_official_picks"], "combinations": data["combination_opportunities"], "tracks": list(data["tracks"])}, indent=2))


if __name__ == "__main__":
    main()
