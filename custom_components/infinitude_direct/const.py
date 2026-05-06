"""Constants for the Infinitude Direct integration."""

DOMAIN = "infinitude_direct"
MANUFACTURER = "Carrier/Bryant"
MODEL = "Infinity"

CONF_HOST = "host"

DEFAULT_HOST = "http://local-infinitude:3001"
SCAN_INTERVAL_SECONDS = 60  # alpha.30: SSE handles live updates; poll is heartbeat

# Temperature bounds (Fahrenheit)
MIN_HEAT_TEMP = 50
MAX_HEAT_TEMP = 90
MIN_COOL_TEMP = 60
MAX_COOL_TEMP = 99
DEFAULT_HEAT_SP = 68
DEFAULT_COOL_SP = 76

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
    "fanonly": "fan_only",
    # Telemetry-reported operational modes (the live state of the unit,
    # distinct from the user-selected config mode). The HA climate
    # entity reads system.mode which is config-side, so these are
    # rarely hit — but if telemetry leaks through anywhere they map
    # to the closest selectable HA mode rather than "off" by default.
    "hpheat": "heat",
    "hpcool": "cool",
    "dehumidify": "cool",
    "defrost": "heat",
    "emheat": "heat",
}

HA_TO_INFINITUDE_HVAC = {
    "off": "off",
    "cool": "cool",
    "heat": "heat",
    "heat_cool": "auto",
    "fan_only": "fanonly",
}
