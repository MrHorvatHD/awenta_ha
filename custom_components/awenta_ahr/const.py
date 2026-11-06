DOMAIN = "awenta_ahr"

PLATFORMS = ["fan", "sensor", "select", "button"]

API_URL = "https://ahr.awenta.pl/api.php"
WS_URL = "wss://ahr.awenta.pl:31990/"

MANUFACTURER = "Awenta"
MODEL = "HRV"

CONF_MODE = "mode"
CONF_PORT = "port"
CONF_DEVICES = "devices"

MODE_LOCAL = "local"
MODE_CLOUD = "cloud"

DEFAULT_PORT = 31990

# Hygrostat: level 0 = off, level n = humidity threshold n * 10 %.
# Timer: levels 0-8 = off, 5, 10, 15, 30, 45, 60, 120, 180 minutes.
HYGROSTAT_OPTIONS = ["Off"] + [f"{level * 10} %" for level in range(1, 10)]
TIMER_MINUTES = [0, 5, 10, 15, 30, 45, 60, 120, 180]
TIMER_OPTIONS = ["Off"] + [f"{minutes} min" for minutes in TIMER_MINUTES[1:]]

# The unit reports which extra option is active: 0 manual, 1 timer, 2 hygrostat.
OPTION_TIMER = 1
OPTION_HYGROSTAT = 2
