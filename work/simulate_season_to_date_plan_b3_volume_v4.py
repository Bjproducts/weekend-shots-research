"""Run the structural higher-volume v4 challenger replay."""
from pathlib import Path

import simulate_season_to_date_plan_b3 as replay

ROOT = Path(__file__).resolve().parents[1]
OVERLAY_PATH = ROOT / "work/season_to_date_plan_b3_volume_v4_spec.json"
overlay = replay.load(OVERLAY_PATH)

replay.SOURCE = ROOT / "outputs/season_to_date_plan_b3"
replay.OUT = ROOT / "outputs/season_to_date_plan_b3_volume_v4"
replay.SPEC_PATH = ROOT / "work/season_to_date_plan_b3_league_balanced_v3_spec.json"
replay.SPEC_OVERLAY = overlay
replay.EFFECTIVE_SPEC_PATH = OVERLAY_PATH

if __name__ == "__main__":
    replay.main()
