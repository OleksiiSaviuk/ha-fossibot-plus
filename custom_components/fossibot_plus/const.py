"""Constants for the FOSSiBOT integration."""

DOMAIN = "fossibot_plus"

# Confirmed via a Charles capture of the real app traffic: the REST API is
# plain HTTP on port 80, NOT HTTPS as the source spec claimed. (Remote
# Address app.fossibot.hk:80, SSL: -, HTTP/1.1.) This is very likely why
# "cannot_connect" happened - aiohttp was attempting a TLS handshake
# against a plain-HTTP endpoint.
BASE_URL = "http://app.fossibot.hk"
LOGIN_ENDPOINT = f"{BASE_URL}/prod-api/app/user/login"
DEVICE_LIST_ENDPOINT = f"{BASE_URL}/prod-api/app/user_device/list"
# INFERRED BY ANALOGY, not yet directly confirmed: since the REST API
# turned out to be plain HTTP rather than HTTPS, the WebSocket is almost
# certainly plain "ws://" too (same server, same port 80 setup). If this
# still fails to connect, capture the WS upgrade request itself in Charles
# (it shows up as a normal HTTP GET with "Upgrade: websocket" headers) and
# confirm scheme/host/port from there.
WS_URL = "ws://app.fossibot.hk/ws"

HEARTBEAT_INTERVAL = 5  # seconds - server drops idle connections after ~15s
RECONNECT_DELAY = 5     # seconds before retrying a dropped websocket

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# --- TLV tags -----------------------------------------------------------
# Confirmed against the sample frame in the source spec (uint32 LE unless
# noted otherwise).
TAG_INPUT_POWER = "0300"       # AC charging input power, watts
TAG_BATTERY_PACK = "0500"      # packs TWO 16-bit sub-values, not one uint32
TAG_TEMP_INVERTER = "1400"     # inverter/FET temperature, deg C
TAG_AC_FREQUENCY = "1600"      # AC mains frequency, raw value / 10 = Hz
TAG_TEMP_BATTERY = "2300"      # battery pack temperature, deg C
TAG_POWER_STATE = "2700"       # main power on/off (0/1)
TAG_AC_OUTPUT = "2b00"         # AC output relay on/off (0/1)
TAG_DC_OUTPUT = "2c00"         # DC (12V) output mode/mask, not a plain bool
TAG_USB_OUTPUT = "2d00"        # USB output mode/mask, not a plain bool
TAG_INPUT_VOLTAGE = "2a00"     # source doc labels this "voltage / current"
                                # with no scale factor - unconfirmed, exposed raw
