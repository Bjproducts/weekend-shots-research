"""Small, deterministic The Odds API adapter for exact 3+ total-shots quotes.

The adapter deliberately exposes only the frozen experiment's market and books.
It never guesses a price and never logs the API key.
"""
from __future__ import annotations

import json
import os
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = "https://api.the-odds-api.com/v4"
TRANSIENT_CODES = {408, 425, 429, 500, 502, 503, 504}


class OddsAPIError(RuntimeError):
    """Safe provider error. Messages never contain credentials."""


class OddsAPIQuotaError(OddsAPIError):
    pass


@dataclass(frozen=True)
class APIResponse:
    payload: Any
    quota_remaining: str | None
    quota_used: str | None
    fetched_utc: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join("".join(char.lower() if char.isalnum() else " " for char in value).split())


def load_local_env(root: Path) -> None:
    """Load simple KEY=VALUE entries without overriding the process environment."""
    path = root / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class TheOddsAPI:
    def __init__(self, api_key: str, timeout: int = 20, retries: int = 3):
        if not api_key:
            raise OddsAPIError("THE_ODDS_API_KEY is not configured")
        self._api_key = api_key
        self.timeout = timeout
        self.retries = retries

    def _get(self, path: str, params: dict[str, Any]) -> APIResponse:
        query = urllib.parse.urlencode({**params, "apiKey": self._api_key})
        url = f"{API_ROOT}/{path.lstrip('/')}?{query}"
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "weekend-shots-research/1"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return APIResponse(
                        payload=payload,
                        quota_remaining=response.headers.get("x-requests-remaining"),
                        quota_used=response.headers.get("x-requests-used"),
                        fetched_utc=utc_now().isoformat(),
                    )
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 401:
                    raise OddsAPIError("The Odds API rejected the configured credential") from None
                if exc.code == 429:
                    if attempt + 1 == self.retries:
                        raise OddsAPIQuotaError("The Odds API quota is exhausted or rate-limited") from None
                elif exc.code not in TRANSIENT_CODES:
                    raise OddsAPIError(f"The Odds API returned HTTP {exc.code}") from None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
            if attempt + 1 < self.retries:
                time.sleep(2**attempt)
        raise OddsAPIError(f"The Odds API request failed after {self.retries} attempts ({type(last_error).__name__})")

    def events(self, sport_key: str) -> APIResponse:
        return self._get(f"sports/{sport_key}/events", {"dateFormat": "iso"})

    def event_player_shots(self, sport_key: str, event_id: str, bookmakers: list[str]) -> APIResponse:
        return self._get(
            f"sports/{sport_key}/events/{event_id}/odds",
            {
                "regions": "us",
                "markets": "player_shots",
                "bookmakers": ",".join(bookmakers),
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
        )


def match_event(
    events: list[dict], home_team: str, away_team: str, kickoff: str, tolerance_minutes: int = 20
) -> dict:
    """Require one unique team-and-kickoff match; ambiguity is a hard rejection."""
    home = normalized_name(home_team)
    away = normalized_name(away_team)
    target = parse_time(kickoff)
    matches = []
    for event in events:
        event_home = normalized_name(event.get("home_team", ""))
        event_away = normalized_name(event.get("away_team", ""))
        commence = event.get("commence_time")
        if not commence:
            continue
        delta = abs((parse_time(commence) - target).total_seconds())
        direct = event_home == home and event_away == away
        if direct and delta <= tolerance_minutes * 60:
            matches.append(event)
    if not matches:
        raise OddsAPIError("No unique provider fixture matched league, teams and kickoff")
    if len(matches) != 1:
        raise OddsAPIError("Ambiguous provider fixture match")
    return matches[0]


def extract_exact_quotes(
    event: dict,
    player: str,
    allowed_books: list[str],
    observed_at: datetime,
    stale_seconds: int,
) -> tuple[list[dict], list[str]]:
    """Extract exact Over 2.5 player_shots quotes and explain rejected records."""
    wanted = normalized_name(player)
    quotes: list[dict] = []
    rejections: list[str] = []
    player_names: set[str] = set()
    for bookmaker in event.get("bookmakers") or []:
        key = bookmaker.get("key")
        if key not in allowed_books:
            continue
        for market in bookmaker.get("markets") or []:
            if market.get("key") != "player_shots":
                continue
            for outcome in market.get("outcomes") or []:
                if normalized_name(outcome.get("description", "")) == wanted:
                    player_names.add(outcome.get("description", ""))
    if len({normalized_name(name) for name in player_names}) > 1:
        return [], ["ambiguous_player_match"]

    for bookmaker in event.get("bookmakers") or []:
        if bookmaker.get("key") not in allowed_books:
            continue
        exact_count = 0
        for market in bookmaker.get("markets") or []:
            if market.get("key") != "player_shots":
                continue
            exact_count += sum(
                normalized_name(outcome.get("description", "")) == wanted
                and outcome.get("name") == "Over"
                and float(outcome.get("point", -1)) == 2.5
                for outcome in market.get("outcomes") or []
            )
        if exact_count > 1:
            return [], [f"{bookmaker.get('key')}:ambiguous_player_match"]

    for bookmaker in event.get("bookmakers") or []:
        key = bookmaker.get("key")
        if key not in allowed_books:
            continue
        for market in bookmaker.get("markets") or []:
            if market.get("key") != "player_shots":
                continue
            updated = market.get("last_update") or bookmaker.get("last_update")
            for outcome in market.get("outcomes") or []:
                if normalized_name(outcome.get("description", "")) != wanted:
                    continue
                if outcome.get("name") != "Over" or float(outcome.get("point", -1)) != 2.5:
                    continue
                if not updated:
                    rejections.append(f"{key}:missing_quote_timestamp")
                    continue
                age = (observed_at - parse_time(updated)).total_seconds()
                if age < -60 or age > stale_seconds:
                    rejections.append(f"{key}:stale_quote")
                    continue
                price = outcome.get("price")
                if not isinstance(price, (int, float)) or price <= 1:
                    rejections.append(f"{key}:invalid_decimal_price")
                    continue
                quotes.append(
                    {
                        "bookmaker": key,
                        "bookmaker_title": bookmaker.get("title", key),
                        "market": "player_shots",
                        "outcome": "Over",
                        "line": 2.5,
                        "price": float(price),
                        "player_provider_name": outcome.get("description"),
                        "last_update": updated,
                        "age_seconds": round(age, 3),
                    }
                )
    if not quotes and not rejections:
        rejections.append("missing_exact_over_2_5_player_shots_market")
    return sorted(quotes, key=lambda row: (row["bookmaker"], -row["price"])), sorted(set(rejections))
