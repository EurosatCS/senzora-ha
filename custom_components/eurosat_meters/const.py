"""Constants for the Eurosat Meters integration."""

DOMAIN = "eurosat_meters"

BASE_URL = "https://cars.eurosat.cz"
PATH_LAST_DATA = "/cnt/apiMeterState/lastData"
PATH_METER_LIST = "/cnt/apiMeterState/gpsUnitMeterList"

CONF_GROUP_ID = "group_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 60  # minutes
MIN_SCAN_INTERVAL = 5  # minutes
MAX_SCAN_INTERVAL = 1440  # minutes
