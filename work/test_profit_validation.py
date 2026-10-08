from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import profit_validation as pv
from the_odds_api import (
    OddsAPIError,
    OddsAPIQuotaError,
    TheOddsAPI,
    extract_exact_quotes,
    match_event,
)


UTC = timezone.utc


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 10, hour, minute, tzinfo=UTC)


def provider_event(updated: str, player: str = "Álex Test", point: float = 2.5, outcome: str = "Over") -> dict:
    return {
        "id": "event-1",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "commence_time": "2026-10-10T12:00:00Z",
        "bookmakers": [
            {
                "key": "draftkings",
                "title": "DraftKings",
                "markets": [
                    {
                        "key": "player_shots",
                        "last_update": updated,
                        "outcomes": [{"name": outcome, "description": player, "point": point, "price": 1.91}],
                    }
                ],
            }
        ],
    }


@contextmanager
def isolated_project():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        old = (pv.BASE, pv.LEDGER, pv.LIVE_BASE)
        pv.BASE = root / "outputs" / "profit_validation"
        pv.LEDGER = pv.BASE / "ledger.jsonl"
        pv.LIVE_BASE = root / "outputs" / "live_plan_b3"
        try:
            yield root
        finally:
            pv.BASE, pv.LEDGER, pv.LIVE_BASE = old


def locked(selection: str, league: str, kickoff: datetime, match: str) -> dict:
    player = selection.split(":")[-1]
    return {
        "weekend": "2026-10-10",
        "selection_id": selection,
        "match_id": match,
        "kickoff": kickoff.isoformat(),
        "league": league,
        "fixture": "Home FC vs Away FC",
        "player_id": player,
        "player": f"Player {player}",
        "home_only": True,
        "plan_b": True,
    }


def quote_payload(selection: dict, observed: datetime, books: dict[str, float], stage: str = "poll") -> dict:
    return {
        **{key: selection[key] for key in ("weekend", "selection_id", "match_id", "league", "fixture", "kickoff", "player_id", "player")},
        "stage": stage,
        "observed_utc": observed.isoformat(),
        "quotes": [
            {
                "bookmaker": book,
                "price": price,
                "last_update": observed.isoformat(),
                "market": "player_shots",
                "outcome": "Over",
                "line": 2.5,
            }
            for book, price in books.items()
        ],
        "rejections": [],
    }


class ProviderMatchingTests(unittest.TestCase):
    def test_exact_fixture_and_home_away_order(self):
        event = provider_event("2026-10-10T11:59:00Z")
        self.assertEqual(match_event([event], "Home FC", "Away FC", "2026-10-10T12:00:00Z")["id"], "event-1")
        with self.assertRaises(OddsAPIError):
            match_event([event], "Away FC", "Home FC", "2026-10-10T12:00:00Z")
        with self.assertRaises(OddsAPIError):
            match_event([event, dict(event)], "Home FC", "Away FC", "2026-10-10T12:00:00Z")

    def test_only_exact_over_2_5_and_allowed_book(self):
        observed = at(12)
        exact, rejected = extract_exact_quotes(provider_event("2026-10-10T11:59:00Z"), "Alex Test", ["draftkings"], observed, 600)
        self.assertEqual(len(exact), 1)
        self.assertEqual(exact[0]["line"], 2.5)
        wrong_line, _ = extract_exact_quotes(provider_event("2026-10-10T11:59:00Z", point=1.5), "Alex Test", ["draftkings"], observed, 600)
        self.assertEqual(wrong_line, [])
        wrong_market, _ = extract_exact_quotes(provider_event("2026-10-10T11:59:00Z", outcome="Under"), "Alex Test", ["draftkings"], observed, 600)
        self.assertEqual(wrong_market, [])
        disallowed, _ = extract_exact_quotes(provider_event("2026-10-10T11:59:00Z"), "Alex Test", ["fanduel"], observed, 600)
        self.assertEqual(disallowed, [])

    def test_stale_and_ambiguous_player_are_rejected(self):
        stale, reasons = extract_exact_quotes(provider_event("2026-10-10T11:40:00Z"), "Alex Test", ["draftkings"], at(12), 600)
        self.assertEqual(stale, [])
        self.assertIn("draftkings:stale_quote", reasons)
        event = provider_event("2026-10-10T11:59:00Z")
        event["bookmakers"][0]["markets"][0]["outcomes"].append(
            {"name": "Over", "description": "Alex-Test", "point": 2.5, "price": 2.1}
        )
        ambiguous, reasons = extract_exact_quotes(event, "Alex Test", ["draftkings"], at(12), 600)
        self.assertEqual(ambiguous, [])
        self.assertIn("draftkings:ambiguous_player_match", reasons)

    def test_api_errors_redact_secret_and_quota_retries(self):
        secret = "never-print-me"
        unauthorized = urllib.error.HTTPError("https://example.invalid", 401, "bad", {}, None)
        with patch("urllib.request.urlopen", side_effect=unauthorized):
            with self.assertRaises(OddsAPIError) as caught:
                TheOddsAPI(secret)._get("sports/x/events", {})
        self.assertNotIn(secret, str(caught.exception))
        limited = urllib.error.HTTPError("https://example.invalid", 429, "limit", {}, None)
        with patch("urllib.request.urlopen", side_effect=limited), patch("time.sleep"):
            with self.assertRaises(OddsAPIQuotaError):
                TheOddsAPI(secret, retries=2)._get("sports/x/events", {})


class LedgerAndRuleTests(unittest.TestCase):
    def test_hash_chain_deduplication_and_tamper_detection(self):
        with isolated_project():
            first = pv.append_event("test", {"value": 1}, "same")
            second = pv.append_event("test", {"value": 2}, "same")
            self.assertEqual(first, second)
            self.assertEqual(len(pv.read_ledger()), 1)
            self.assertEqual(pv.reconcile_ledger(), [])
            row = pv.read_ledger()[0]
            row["payload"]["value"] = 99
            pv.LEDGER.write_text(json.dumps(row) + "\n", encoding="utf-8")
            self.assertTrue(pv.reconcile_ledger())

    def test_confirmed_home_standard_lineup_enforced(self):
        with isolated_project() as root:
            weekend = "2026-10-10"
            folder = pv.LIVE_BASE / weekend
            (folder / "lineup_decisions").mkdir(parents=True)
            board = {
                "ranking_version": "live-plan-b3-league-balanced-v3",
                "candidates": [{"match_id": "m1", "player_id": "p1"}, {"match_id": "m1", "player_id": "p2"}],
            }
            (folder / "frozen_board_league_balanced_v3.json").write_text(json.dumps(board), encoding="utf-8")
            base = {
                "locked_utc": at(11).isoformat(), "match_id": "m1", "date": at(12).isoformat(),
                "league": "MLS", "fixture": "Home FC vs Away FC", "lineup_type": "standard",
                "confirmed_home_starter_ids": ["p1", *[f"x{i}" for i in range(10)]],
                "rejected_provisional_candidates": [],
            }
            base["official_picks"] = [
                {"player_id": "p1", "player": "Home", "candidate_side": "home", "plan_B": True},
                {"player_id": "p2", "player": "Away", "candidate_side": "away", "plan_B": True},
            ]
            (folder / "lineup_decisions" / "m1.json").write_text(json.dumps(base), encoding="utf-8")
            result = pv.sync_official_selections(weekend)
            self.assertEqual(result["imported"], 1)
            self.assertEqual(len(pv.locked_selections()), 1)
            rejects = [row for row in pv.read_ledger() if row["event_type"] == "selection_rejected"]
            self.assertIn("not_home_player", rejects[0]["payload"]["reasons"])
            self.assertIn("not_confirmed_home_starter", rejects[0]["payload"]["reasons"])

    def test_no_lookahead_and_quote_immutability(self):
        with isolated_project():
            selection = locked("w:m:p1", "MLS", at(12), "m")
            pv.append_event("selection_locked", selection, "s1", at(11))
            past = quote_payload(selection, at(11, 54), {"draftkings": 1.9})
            future = quote_payload(selection, at(11, 56), {"draftkings": 2.2})
            pv.append_event("quote_snapshot", past, "q1", at(11, 54))
            pv.append_event("quote_snapshot", future, "q2", at(11, 56))
            chosen = pv.latest_usable_quote(selection, at(11, 55), pv.read_ledger())
            self.assertEqual(chosen["quotes"][0]["price"], 1.9)
            path = pv.BASE / "snapshot.json"
            pv.write_once(path, past)
            with self.assertRaises(RuntimeError):
                pv.write_once(path, future)


class TicketTests(unittest.TestCase):
    def add_selection_and_quote(self, selection: dict, observed: datetime, books: dict[str, float]) -> None:
        pv.append_event("selection_locked", selection, f"s:{selection['selection_id']}", observed - timedelta(hours=1))
        pv.append_event("quote_snapshot", quote_payload(selection, observed, books), f"q:{selection['selection_id']}", observed)

    def test_same_book_grouping_one_per_league_and_no_duplicate_leg(self):
        with isolated_project():
            observed = at(11, 55)
            a = locked("w:m1:p1", "MLS", at(12), "m1")
            b = locked("w:m2:p2", "Premier League", at(12), "m2")
            duplicate_league = locked("w:m3:p3", "MLS", at(12), "m3")
            self.add_selection_and_quote(a, at(11, 54), {"draftkings": 1.8, "fanduel": 2.0})
            self.add_selection_and_quote(b, at(11, 54), {"draftkings": 2.0, "fanduel": 1.7})
            self.add_selection_and_quote(duplicate_league, at(11, 54), {"draftkings": 10.0, "fanduel": 10.0})
            result = pv.freeze_due_tickets("2026-10-10", observed)
            ticket = result["ticket"]
            self.assertEqual(ticket["bookmaker"], "draftkings")
            self.assertEqual(len(ticket["legs"]), 2)
            self.assertEqual(len({leg["league"] for leg in ticket["legs"]}), 2)
            self.assertEqual(ticket["stake"], 90.0)
            self.assertEqual(ticket["price_type"], "derived_product_price")
            again = pv.freeze_due_tickets("2026-10-10", observed)
            prior_ids = {leg["selection_id"] for leg in ticket["legs"]}
            if again.get("ticket"):
                self.assertTrue(prior_ids.isdisjoint({leg["selection_id"] for leg in again["ticket"]["legs"]}))

    def test_missing_common_book_produces_no_combo(self):
        with isolated_project():
            a = locked("w:m1:p1", "MLS", at(12), "m1")
            b = locked("w:m2:p2", "Bundesliga", at(12), "m2")
            self.add_selection_and_quote(a, at(11, 54), {"draftkings": 2.0})
            self.add_selection_and_quote(b, at(11, 54), {"fanduel": 2.0})
            result = pv.freeze_due_tickets("2026-10-10", at(11, 55))
            self.assertEqual(result["status"], "no_common_book")
            self.assertEqual(len(pv.ticket_events()), 0)

    def test_overlapping_90_percent_exposure_is_flagged(self):
        with isolated_project():
            first = {
                "weekend": "2026-10-10", "ticket_id": "t0", "bookmaker": "draftkings", "stake": 90.0,
                "executability": "executable", "legs": [], "freeze_for_earliest_kickoff": at(11).isoformat(),
            }
            pv.append_event("ticket_created", first, "t0")
            a = locked("w:m1:p1", "MLS", at(12), "m1")
            b = locked("w:m2:p2", "Bundesliga", at(12), "m2")
            self.add_selection_and_quote(a, at(11, 54), {"draftkings": 2.0})
            self.add_selection_and_quote(b, at(11, 54), {"draftkings": 2.0})
            ticket = pv.freeze_due_tickets("2026-10-10", at(11, 55))["ticket"]
            self.assertEqual(ticket["stake"], 90.0)
            self.assertEqual(ticket["executability"], "non_executable_overlap")
            self.assertEqual(ticket["cumulative_exposure_after"], 180.0)

    def test_win_loss_void_repricing_and_clv(self):
        with isolated_project():
            weekend = "2026-10-10"
            settled_dir = pv.LIVE_BASE / weekend / "settled"
            settled_dir.mkdir(parents=True)
            legs = []
            picks = []
            for index, shots in enumerate((4, None, 3), 1):
                selection = locked(f"{weekend}:m{index}:p{index}", ["MLS", "Bundesliga", "Premier League"][index - 1], at(12), f"m{index}")
                legs.append({**selection, "bookmaker": "draftkings", "price": 2.0, "quote_last_update": at(11, 54).isoformat()})
                picks.append({"player_id": f"p{index}", "shots": shots, "minutes": 90 if shots is not None else None})
                close = quote_payload(selection, at(11, 59), {"draftkings": 1.8}, "final_pre_kickoff")
                pv.append_event("quote_snapshot", close, f"close:{index}", at(11, 59))
                (settled_dir / f"m{index}.json").write_text(json.dumps({"match_id": f"m{index}", "official_picks": [picks[-1]]}), encoding="utf-8")
            ticket = {
                "weekend": weekend, "ticket_id": "ticket-win", "bookmaker": "draftkings", "stake": 90.0,
                "derived_product_price": 8.0, "executability": "executable", "legs": legs,
                "freeze_for_earliest_kickoff": at(12).isoformat(),
            }
            pv.append_event("ticket_created", ticket, "ticket-win")
            result = pv.settle_tickets(weekend, at(15))
            self.assertEqual(result["settled"], 1)
            settlement = pv.settlement_events()[0]
            self.assertEqual(settlement["result"], "win")
            self.assertEqual(settlement["settled_leg_count"], 2)
            self.assertEqual(settlement["repriced_derived_odds"], 4.0)
            self.assertEqual(settlement["bankroll_after"], 370.0)
            self.assertGreater(settlement["combo_clv"], 0)

    def test_fewer_than_two_nonvoid_legs_voids_ticket(self):
        with isolated_project():
            weekend = "2026-10-10"
            settled_dir = pv.LIVE_BASE / weekend / "settled"
            settled_dir.mkdir(parents=True)
            legs = []
            for index, shots in enumerate((4, None), 1):
                selection = locked(f"{weekend}:m{index}:p{index}", ["MLS", "Bundesliga"][index - 1], at(12), f"m{index}")
                legs.append({**selection, "bookmaker": "draftkings", "price": 2.0})
                (settled_dir / f"m{index}.json").write_text(json.dumps({"match_id": f"m{index}", "official_picks": [{"player_id": f"p{index}", "shots": shots}]}), encoding="utf-8")
            pv.append_event("ticket_created", {"weekend": weekend, "ticket_id": "t", "bookmaker": "draftkings", "stake": 90.0, "executability": "executable", "legs": legs, "freeze_for_earliest_kickoff": at(12).isoformat()}, "t")
            pv.settle_tickets(weekend, at(15))
            settlement = pv.settlement_events()[0]
            self.assertEqual(settlement["result"], "void")
            self.assertEqual(settlement["bankroll_after"], 100.0)

    def test_overlapping_losses_can_cause_insolvency_and_stop_new_tickets(self):
        with isolated_project():
            weekend = "2026-10-10"
            settled_dir = pv.LIVE_BASE / weekend / "settled"
            settled_dir.mkdir(parents=True)
            tickets = []
            for ticket_index in range(2):
                legs = []
                for leg_index, league in enumerate(("MLS", "Bundesliga"), 1):
                    number = ticket_index * 2 + leg_index
                    selection = locked(f"{weekend}:m{number}:p{number}", league, at(12), f"m{number}")
                    legs.append({**selection, "bookmaker": "draftkings", "price": 2.0})
                    (settled_dir / f"m{number}.json").write_text(
                        json.dumps({"match_id": f"m{number}", "official_picks": [{"player_id": f"p{number}", "shots": 1}]}),
                        encoding="utf-8",
                    )
                ticket = {
                    "weekend": weekend, "ticket_id": f"loss-{ticket_index}", "bookmaker": "draftkings",
                    "stake": 90.0, "executability": "executable" if ticket_index == 0 else "non_executable_overlap",
                    "legs": legs, "freeze_for_earliest_kickoff": at(12).isoformat(),
                }
                pv.append_event("ticket_created", ticket, f"loss-ticket-{ticket_index}")
            pv.settle_tickets(weekend, at(15))
            state = pv.bankroll_state()
            self.assertEqual(state["bankroll"], -80.0)
            self.assertTrue(state["insolvent"])
            summary = pv.build_summary()
            self.assertEqual(summary["tickets"], 2)
            self.assertEqual(summary["settled_tickets"], 2)
            self.assertEqual(summary["paper_net_profit"], -180.0)


if __name__ == "__main__":
    unittest.main()
