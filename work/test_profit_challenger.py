from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import live_plan_b3_volume_v4 as live_v4
import profit_challenger as pc
import profit_validation as pv
import shared_quote_store as shared
from the_odds_api import APIResponse

UTC = timezone.utc


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 10, hour, minute, tzinfo=UTC)


@contextmanager
def isolated():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        previous = (pc.BASE, pc.LEDGER, pv.LIVE_BASE, shared.BASE)
        pc.BASE = root / "profit_challenger"
        pc.LEDGER = pc.BASE / "ledger.jsonl"
        pv.LIVE_BASE = root / "live"
        shared.BASE = root / "shared"
        try:
            yield root
        finally:
            pc.BASE, pc.LEDGER, pv.LIVE_BASE, shared.BASE = previous


def selection(suffix: str, league: str, match: str, kickoff: datetime | None = None) -> dict:
    weekend = "2026-10-10"
    kickoff = kickoff or at(12)
    return {
        "strategy_id": "volume_v4", "weekend": weekend,
        "selection_id": f"{weekend}:{match}:{suffix}", "quote_subject_id": f"{weekend}:{match}:{suffix}",
        "match_id": match, "kickoff": kickoff.isoformat(), "league": league,
        "fixture": f"Home {match} vs Away {match}", "player_id": suffix, "player": f"Player {suffix}",
        "home_only": True, "plan_b": True,
    }


def quote(item: dict, price: float = 2.0) -> dict:
    return {
        **{key: item[key] for key in ("strategy_id", "weekend", "selection_id", "quote_subject_id", "match_id", "league", "fixture", "kickoff", "player_id", "player")},
        "stage": "poll", "observed_utc": at(11, 54).isoformat(),
        "quotes": [{"bookmaker": "draftkings", "price": price, "last_update": at(11, 54).isoformat(), "market": "player_shots", "outcome": "Over", "line": 2.5}],
        "rejections": [],
    }


class FakeAPI:
    def __init__(self):
        self.calls = 0

    def event_player_shots(self, sport_key, event_id, bookmakers):
        self.calls += 1
        payload = {
            "id": event_id,
            "bookmakers": [{"key": "draftkings", "title": "DraftKings", "markets": [{"key": "player_shots", "last_update": at(11, 54).isoformat(), "outcomes": [{"name": "Over", "description": "Player p1", "point": 2.5, "price": 1.9}]}]}],
        }
        return APIResponse(payload, "99", "1", at(11, 54).isoformat())


class ChallengerTests(unittest.TestCase):
    def test_started_fixture_refusal_is_immutable_and_enters_ledger(self):
        with isolated() as root:
            previous = live_v4.BASE
            live_v4.BASE = pv.LIVE_BASE
            try:
                weekend = "2026-10-10"
                folder = live_v4.BASE / weekend
                folder.mkdir(parents=True)
                candidate = {
                    "match_id": "m1", "player_id": "p1", "player": "Frozen",
                    "candidate_side": "home", "plan_B": True, "avg_shots": 4.0,
                    "avg_minutes": 90, "league": "MLS", "date": at(12).isoformat(),
                }
                board = {
                    "ranking_version": "live-plan-b3-volume-v4",
                    "candidates": [candidate],
                    "selected_environments": [{
                        "match_id": "m1", "date": at(12).isoformat(), "league": "MLS",
                        "fixture": "Home vs Away", "plan_B_candidates": [candidate],
                    }],
                }
                (folder / "frozen_board_volume_v4.json").write_text(json.dumps(board), encoding="utf-8")
                started = {"general": {"started": True, "finished": False}, "content": {}}
                with patch.object(live_v4, "get_json", return_value=started):
                    result = live_v4.lineups(weekend)
                refusal_path = folder / "lineup_refusals_volume_v4/m1.json"
                original = refusal_path.read_bytes()
                self.assertEqual(result["refused_after_start"][0]["player"], "Frozen")
                self.assertFalse(json.loads(original)["official_selection_eligible"])
                self.assertFalse(json.loads(original)["outcome_accessed"])

                with patch.object(live_v4, "get_json", side_effect=AssertionError("immutable refusal must skip refetch")):
                    live_v4.lineups(weekend)
                self.assertEqual(refusal_path.read_bytes(), original)

                sync = pc.sync_official_selections(weekend)
                self.assertEqual(sync["imported"], 0)
                self.assertEqual(sync["rejected"], 1)
                records = pc.read_ledger()
                rejection = next(row for row in records if row["event_type"] == "selection_rejected")
                self.assertEqual(rejection["payload"]["reasons"], ["kickoff_window_missed_already_started_or_finished"])
                self.assertFalse(rejection["payload"]["official_selection_eligible"])
            finally:
                live_v4.BASE = previous

    def test_rejected_frozen_candidate_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = live_v4.BASE
            live_v4.BASE = Path(directory)
            try:
                weekend = "2026-10-10"
                folder = live_v4.BASE / weekend
                folder.mkdir(parents=True)
                candidate = {"match_id": "m1", "player_id": "p1", "player": "Frozen", "candidate_side": "home", "plan_B": True, "avg_shots": 4.0, "avg_minutes": 90}
                board = {
                    "candidates": [candidate],
                    "selected_environments": [{"match_id": "m1", "date": at(12).isoformat(), "league": "MLS", "fixture": "Home vs Away", "plan_B_candidates": [candidate]}],
                }
                (folder / "frozen_board_volume_v4.json").write_text(json.dumps(board), encoding="utf-8")
                missing = {"general": {"started": False, "finished": False}, "content": {"lineup": {"lineupType": "standard", "source": "test", "homeTeam": {"starters": [{"id": f"x{i}"} for i in range(11)]}}}}
                confirmed = {"general": {"started": False, "finished": False}, "content": {"lineup": {"lineupType": "standard", "source": "test", "homeTeam": {"starters": [{"id": "p1"}, *[{"id": f"x{i}"} for i in range(10)]]}}}}
                with patch.object(live_v4, "get_json", return_value=missing):
                    live_v4.lineups(weekend)
                decision_path = folder / "lineup_decisions_volume_v4/m1.json"
                rejected_hash = decision_path.read_bytes()
                with patch.object(live_v4, "get_json", return_value=confirmed):
                    live_v4.lineups(weekend)
                self.assertEqual(decision_path.read_bytes(), rejected_hash)
                self.assertEqual(json.loads(rejected_hash)["official_picks"], [])
            finally:
                live_v4.BASE = previous

    def test_shared_physical_quote_is_fetched_once(self):
        with isolated():
            item = selection("p1", "MLS", "m1")
            events = [{"id": "e1", "home_team": "Home m1", "away_team": "Away m1", "commence_time": at(12).isoformat()}]
            api = FakeAPI()
            first = shared.capture(weekend=item["weekend"], selection=item, stage="poll", observed=at(11, 54), sport_key="soccer_usa_mls", allowed_bookmakers=["draftkings"], stale_seconds=600, api=api, events=events)
            second = shared.capture(weekend=item["weekend"], selection={**item, "strategy_id": "league_balanced_v3"}, stage="poll", observed=at(11, 54), sport_key="soccer_usa_mls", allowed_bookmakers=["draftkings"], stale_seconds=600, api=api, events=events)
            self.assertEqual(api.calls, 1)
            self.assertEqual(first["observation_id"], second["observation_id"])
            self.assertTrue(second["cache_hit"])

    def test_two_per_league_one_per_fixture_and_dual_tracks(self):
        with isolated():
            items = [
                selection("p1", "MLS", "m1"),
                selection("p2", "MLS", "m2"),
                selection("p3", "Premier League", "m3"),
                selection("p4", "MLS", "m4"),
            ]
            with pc.challenger_context():
                for item in items:
                    pv.append_event("selection_locked", item, "s:" + item["selection_id"], at(11))
                    pv.append_event("quote_snapshot", quote(item), "q:" + item["selection_id"], at(11, 54))
                result = pv.freeze_due_tickets("2026-10-10", at(11, 55))
                tickets = result["tickets"]
                self.assertEqual({row["staking_track"] for row in tickets}, {"fixed_10", "stress_90"})
                for ticket in tickets:
                    self.assertEqual(len(ticket["legs"]), 3)
                    self.assertLessEqual(max(Counter(leg["league"] for leg in ticket["legs"]).values()), 2)
                    self.assertEqual(len({leg["match_id"] for leg in ticket["legs"]}), 3)
                fixed = next(row for row in tickets if row["staking_track"] == "fixed_10")
                stress = next(row for row in tickets if row["staking_track"] == "stress_90")
                self.assertEqual(fixed["stake"], 10.0)
                self.assertEqual(stress["stake"], 90.0)
                self.assertEqual(fixed["combo_id"], stress["combo_id"])

    def test_overlap_is_track_specific_and_promotion_uses_fixed_10(self):
        with isolated():
            with pc.challenger_context():
                pv.append_event("ticket_created", {"strategy_id": "volume_v4", "staking_track": "fixed_10", "weekend": "2026-10-10", "combo_id": "old", "ticket_id": "old:fixed_10", "stake": 95.0, "executability": "executable", "legs": [], "freeze_for_earliest_kickoff": at(11).isoformat()}, "old-fixed")
                pv.append_event("ticket_created", {"strategy_id": "volume_v4", "staking_track": "stress_90", "weekend": "2026-10-10", "combo_id": "old", "ticket_id": "old:stress_90", "stake": 5.0, "executability": "executable", "legs": [], "freeze_for_earliest_kickoff": at(11).isoformat()}, "old-stress")
                self.assertEqual(pv.bankroll_state(staking_track="fixed_10")["outstanding_exposure"], 95.0)
                self.assertEqual(pv.bankroll_state(staking_track="stress_90")["outstanding_exposure"], 5.0)
            summary = pc.build_summary()
            self.assertFalse(summary["historical_assumed_prices_included"])
            self.assertIn("maximum_drawdown", summary["promotion_checks"])
            self.assertEqual(summary["staking_tracks"]["fixed_10"]["stake_fraction"], 0.1)

    def test_dual_track_settlements_use_independent_bankrolls(self):
        with isolated():
            weekend = "2026-10-10"
            items = [selection("p1", "MLS", "m1"), selection("p2", "Premier League", "m2")]
            settled = pv.LIVE_BASE / weekend / "settled_volume_v4"
            settled.mkdir(parents=True)
            for item in items:
                (settled / f"{item['match_id']}.json").write_text(
                    json.dumps({"match_id": item["match_id"], "official_picks": [{"player_id": item["player_id"], "shots": 3, "minutes": 90}]}),
                    encoding="utf-8",
                )
            with pc.challenger_context():
                for track, stake in (("fixed_10", 10.0), ("stress_90", 90.0)):
                    ticket = {
                        "strategy_id": "volume_v4", "staking_track": track, "weekend": weekend,
                        "combo_id": "combo", "ticket_id": f"combo:{track}", "bookmaker": "draftkings",
                        "stake": stake, "derived_product_price": 4.0, "executability": "executable",
                        "freeze_for_earliest_kickoff": at(12).isoformat(),
                        "legs": [{**item, "bookmaker": "draftkings", "price": 2.0} for item in items],
                    }
                    pv.append_event("ticket_created", ticket, "ticket:" + track)
                result = pv.settle_tickets(weekend, at(15))
                self.assertEqual(result["settled"], 2)
                self.assertEqual(pv.bankroll_state(staking_track="fixed_10")["bankroll"], 130.0)
                self.assertEqual(pv.bankroll_state(staking_track="stress_90")["bankroll"], 370.0)


if __name__ == "__main__":
    unittest.main()
