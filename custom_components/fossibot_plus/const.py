"""Constants for the FOSSiBOT integration."""

DOMAIN = "fossibot_plus"

BASE_URL = "http://app.fossibot.hk"
LOGIN_ENDPOINT = f"{BASE_URL}/prod-api/app/user/login"
DEVICE_LIST_ENDPOINT = f"{BASE_URL}/prod-api/app/user_device/list"
CONTROL_ENDPOINT = f"{BASE_URL}/prod-api/app/ctrl/route"
WS_URL = "ws://app.fossibot.hk/ws"

HEARTBEAT_INTERVAL = 5        # seconds — server drops idle connections after ~15s
RECONNECT_DELAY = 5           # seconds before retrying a dropped websocket
FRAME_SILENCE_TIMEOUT = 30    # seconds — watchdog: force-reconnect if no frame arrives
DEVICE_STATUS_POLL_INTERVAL = 60  # seconds — REST poll for online/offline state

LOGIN_DUPLICATE_SUBMIT_MARKER = "重复提交"
LOGIN_RETRY_DELAY = 6         # seconds — pause before retrying after anti-dup guard
LOGIN_MAX_RETRIES = 2

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Control command format (reverse-engineered from captured requests):
#   cmd = PREFIX + tag(2B LE) + value(4B LE) + CRC16/MODBUS(tag+value, big-endian)
CTRL_COMMAND_PREFIX = "0e000c000800"

# ---------------------------------------------------------------------------
# TLV tag map
# Derived from live WS captures cross-checked against the app screen,
# and from captured control commands. See DEVELOPMENT.md for full history.
# ---------------------------------------------------------------------------

# ✅ CONFIRMED — matched against app readout AND/OR control-command tag:
TAG_BATTERY_SOC       = "0100"  # battery %, matches app SOC exactly
TAG_TEMPERATURE       = "0200"  # °C, low 16 bits only (some models pack metadata
                                 # in the high 16 bits — taking only low16 is safe
                                 # for all observed models: 22→22, 196638→30)
TAG_REMAINING_MINUTES  = "0300"  # minutes to full/empty (NOT watts as spec claimed)
TAG_CHARGING_ACTIVE    = "0400"  # 1=charging, 0=idle/full — confirmed by transitions
TAG_AC_GRID_POWER      = "1300"  # AC mains input power (W, scale 1:1) — only nonzero
                                  # while charging from grid; mutually exclusive with
                                  # TAG_AC_OUTPUT_POWER (never both nonzero simultaneously)
TAG_AC_OUTPUT_POWER    = "1400"  # AC output power (W). When USB is also active,
                                  # 1400 = AC only, 2300 = 1400 + 2500 (total). Confirmed
                                  # by exact match with app readout at two power levels.
TAG_AC_OUTPUT_VOLTAGE  = "1500"  # AC output voltage, raw*0.1=V (~231 V when AC on)
TAG_AC_FREQUENCY       = "1600"  # AC output frequency, raw*0.1=Hz (500→50.0 Hz)
TAG_LED_MODE           = "2600"  # LED: 0=off, 1=steady, 2=SOS, 3=strobe — confirmed
                                  # from 4 captured ctrl cmds + live WS (0/1/3 seen)
TAG_AC_STATE           = "2700"  # AC output on/off (0/1) — confirmed by ctrl cmd
TAG_DC_STATE           = "2800"  # DC output on/off (0/1) — confirmed by ctrl cmd
TAG_USB_STATE          = "2900"  # USB output on/off (0/1) — confirmed by ctrl cmd
TAG_OUTPUT_MEMORY      = "2b00"  # Output memory (retain state after power loss):
                                  # 0=off, 1=on — confirmed from ctrl cmd + transitions
TAG_SCREEN_TIMEOUT     = "2c00"  # Screen auto-off: 0=always on, 1=30s, 2=1min,
                                  # 3=5min, 4=10min, 5=30min — user-confirmed
TAG_POWER_OFF_TIMER    = "2d00"  # Auto power-off: 0=never, 1=5min, 2=10min,
                                  # 3=1h, 4=8h — user-confirmed
TAG_CHARGE_MODE        = "2e00"  # Charge mode: 0=UPS, 1=ECO — confirmed by ctrl cmds
TAG_SOUND              = "3300"  # Sound: 0=off, 1=on — confirmed by ctrl cmd

TAG_TOTAL_INPUT_POWER  = "2200"  # Total input power = grid AC + solar PV (W, scale 1:1)
TAG_CHARGE_POWER       = "2a00"  # AC charge power limit (W) — set by number entity

# ✅ CONFIRMED from log analysis (frames with USB active):
#   2300 = 1400 + 2500 in every observed frame — 100% match across 6 samples.
#   1400 = AC output only; 2500 = USB output only; 2300 = all outputs combined.
TAG_TOTAL_OUTPUT_POWER = "2300"  # Total output power (AC + USB + DC) (W)
TAG_USB_OUTPUT_POWER   = "2500"  # USB output power (W) — zero when USB off,
                                  # nonzero while USB active; moves independently
                                  # from 1400 and always satisfies 2300=1400+2500

# --- Model detection from serial number ------------------------------------
# Serial numbers encode the model in the first 4 characters:
#   F180... → F1800 series (max charge 1200 W)
#   F300... → F3000 series (max charge 2000 W)
#   anything else → treated as unknown (safe 2000 W ceiling)

CHARGE_POWER_LIMITS: dict[str, dict] = {
    "f1800":  {"min": 100, "max": 1200, "step": 100},
    "f3000":  {"min": 100, "max": 2000, "step": 100},
    "custom": {"min": 100, "max": 2000, "step": 100},
}


def detect_model(sn_code: str) -> str:
    """Detect model family from the serial number prefix."""
    sn = sn_code.upper()
    if sn.startswith("F180"):
        return "f1800"
    if sn.startswith("F300"):
        return "f3000"
    return "custom"
