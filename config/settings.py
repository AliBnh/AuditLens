# config/settings.py
# All project-wide constants. Never hardcode these in notebooks or scripts.

from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
OUTPUTS = ROOT_DIR / "outputs"

# API
SECOP_ENDPOINT = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
API_PAGE_SIZE = 50_000

# Date scope
TRAIN_START = "2019-01-01"
TRAIN_END   = "2021-12-31"
VALID_START = "2022-01-01"
VALID_END   = "2022-08-06"

# SMMLV by year (Colombian minimum wage, used for threshold calculations)
SMMLV = {
    2019: 828_116,
    2020: 877_803,
    2021: 908_526,
    2022: 1_000_000,
    2023: 1_160_000,
}

# Risk index weights (empirically validated, tier-aware ranking with community detection)
WEIGHT_PROCESS_ANOMALY = 0.55
WEIGHT_SPLITTING       = 0.25
WEIGHT_NETWORK         = 0.10
WEIGHT_COMMUNITY       = 0.10

# Risk tier thresholds
TIER_LOW    = 0.3
TIER_HIGH   = 0.6

# Splitting detection
SPLITTING_WINDOWS_DAYS = [30, 60, 90]
THRESHOLD_PROXIMITY_PCT = 0.10   # within 10% below audit threshold

# Anomaly detection
CONTAMINATION_RATE = 0.05        # top 5% flagged

# Drift monitoring
PSI_MONITOR_THRESHOLD = 0.10
PSI_RETRAIN_THRESHOLD = 0.20

# Random seed — use everywhere
RANDOM_STATE = 42