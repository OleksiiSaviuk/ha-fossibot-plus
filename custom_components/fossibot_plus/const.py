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

# The backend has a RuoYi-style anti-duplicate-submission guard: an
# identical login body sent again within a few seconds of a previous one
# gets rejected with msg "不允许重复提交，请稍候再试" even though the
# credentials are correct. This happens in practice because the config
# flow does one login to validate credentials, and async_setup_entry does
# a second one moments later with a fresh client. Retry instead of
# failing outright when this specific message is seen.
LOGIN_DUPLICATE_SUBMIT_MARKER = "重复提交"
LOGIN_RETRY_DELAY = 6  # seconds - comfortably past the guard's window
LOGIN_MAX_RETRIES = 2

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# --- TLV tags -------------------------------------------------------------
# Re-derived from a real live capture (custom_components.fossibot_plus debug
# log) cross-checked against the FOSSiBOT+ app screen at the same moment,
# on 2026-09-26. The original source spec's tag table turned out to be
# wrong or incomplete in several places - see the notes on each tag below
# and README.md/DEVELOPMENT.md for the full reasoning.

# CONFIRMED (exact numeric match against the app, on two different frames):
TAG_BATTERY_SOC = "0100"          # battery %, matches app's SOC readout exactly
TAG_TEMPERATURE = "0200"          # deg C, matches the single dial-icon temperature
TAG_REMAINING_MINUTES = "0300"    # minutes until full/empty. The source spec called
                                   # this "AC input power" - wrong. 67h00m -> 4020,
                                   # 12h45m -> 765, both matched exactly to the
                                   # app's "X год Y хв" readout. There is currently
                                   # NO confirmed tag for input/output power in watts.
TAG_AC_FREQUENCY = "1600"         # raw / 10 = Hz. AC on -> 500 (50.0Hz), AC off -> 0
TAG_POWER_STATE = "2700"          # main power on/off (0/1)
TAG_AC_OUTPUT = "2b00"            # AC output relay on/off (0/1) - confirmed BOTH
                                   # directions: 0 with the app's AC toggle off,
                                   # 1 with it on

# UNCONFIRMED / likely wrong as originally documented - kept only as raw
# diagnostics, disabled by default in sensor.py:
TAG_UNKNOWN_1400 = "1400"         # source spec called this "inverter temperature".
                                   # In the one live sample so far its value (11)
                                   # happened to equal the app's output power (11W)
                                   # - could be power, could be coincidence with a
                                   # real temperature. Needs a second data point at
                                   # a different, distinctly non-11 output wattage.
TAG_UNKNOWN_2300 = "2300"         # same situation/caveat as TAG_UNKNOWN_1400.
TAG_BATTERY_PACK = "0500"         # NOT actually two packed 16-bit sub-values as
                                   # previously assumed - that was a misreading on
                                   # my part. The real frame has a separate,
                                   # currently-unmapped tag "1200" right after it;
                                   # 0500's own raw uint32 value has no known
                                   # physical meaning yet. Exposed raw, unconfirmed.
TAG_DC_OUTPUT = "2c00"            # NOT a DC on/off flag: stayed at raw value 2 in
                                   # BOTH a live capture with DC toggled ON and one
                                   # with it toggled OFF. Likely a static value (e.g.
                                   # a port count) rather than live state.
TAG_USB_OUTPUT = "2d00"           # same caveat as TAG_DC_OUTPUT - only ever observed
                                   # while USB was off in both captures so far, but
                                   # its constancy alongside TAG_DC_OUTPUT's behavior
                                   # makes "static value, not on/off" the likely case.
TAG_INPUT_VOLTAGE = "2a00"        # stayed at a constant raw 400 across two captures
                                   # with very different power states - likely a
                                   # static/rated spec value, not a live measurement.

