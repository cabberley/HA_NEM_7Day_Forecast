"""Constants for the NEM PD7DAY integration."""

import re

DOMAIN = "nem_pd7day"

CONF_REGIONS = "regions"

DEFAULT_REGIONS = ["QLD1"]
REGION_OPTIONS = ["QLD1", "NSW1", "VIC1", "SA1", "TAS1"]

SCAN_INTERVAL_SECONDS = 3600
PLATFORMS = ["sensor"]

AEMO_WWW = "https://aemo.com.au/"
ATTRIBUTION = "Data provided by AEMO"

BASE_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/PD7Day/"
FILE_PATTERN = re.compile(r"PUBLIC_PD7DAY_.*\.(ZIP|CSV)$", re.IGNORECASE)
FILE_DT_PATTERN = re.compile(r"(\d{14}|\d{12})")
