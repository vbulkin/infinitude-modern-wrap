"""Constants for the Infinitude Direct integration."""

DOMAIN = "infinitude_direct"
MANUFACTURER = "Carrier/Bryant"
MODEL = "Infinity"

CONF_HOST = "host"

DEFAULT_HOST = "http://local-infinitude:3000"
SCAN_INTERVAL_SECONDS = 30

PRESET_HOME = "home"
PRESET_AWAY = "away"
PRESET_SLEEP = "sleep"
PRESET_WAKE = "wake"
PRESET_MODES = [PRESET_HOME, PRESET_AWAY, PRESET_SLEEP, PRESET_WAKE]

INFINITUDE_TO_HA_HVAC = {
    "off": "off",
    "cool": "cool",
    "heat": "heat",
    "auto": "heat_cool",
    "heatcool": "heat_cool",
    "fanonly": "fan_only",
}

HA_TO_INFINITUDE_HVAC = {
    "off": "off",
    "cool": "cool",
    "heat": "heat",
    "heat_cool": "auto",
    "fan_only": "fanonly",
}
