"""Run the user-requested home-only, consistency-first v2 replay."""
from pathlib import Path

import simulate_season_to_date_plan_b3 as replay

ROOT = Path(__file__).resolve().parents[1]
replay.SOURCE = ROOT / "outputs/season_to_date_plan_b3"
replay.OUT = ROOT / "outputs/season_to_date_plan_b3_consistency_v2"
replay.SPEC_PATH = ROOT / "work/season_to_date_plan_b3_consistency_v2_spec.json"

if __name__ == "__main__":
    replay.main()
