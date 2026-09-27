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
# Confirmed by successfully replaying six captured commands byte-for-byte
# (see CTRL_COMMAND_PREFIX below) - same host/scheme as login and device list.
CONTROL_ENDPOINT = f"{BASE_URL}/prod-api/app/ctrl/route"
# INFERRED BY ANALOGY, not yet directly confirmed: since the REST API
# turned out to be plain HTTP rather than HTTPS, the WebSocket is almost
# certainly plain "ws://" too (same server, same port 80 setup). If this
# still fails to connect, capture the WS upgrade request itself in Charles
# (it shows up as a normal HTTP GET with "Upgrade: websocket" headers) and
# confirm scheme/host/port from there.
WS_URL = "ws://app.fossibot.hk/ws"

HEARTBEAT_INTERVAL = 5  # seconds - server drops idle connections after ~15s
RECONNECT_DELAY = 5     # seconds before retrying a dropped websocket

# Watchdog: normal server push cadence is ~1 frame/second (measured from a
# live capture). Seen in the field: the WS connection can die silently at
# the network level (no close frame, no exception - likely a NAT/proxy
# dropping an idle TCP session without FIN/RST) and `heartbeat=None` on
# ws_connect means aiohttp won't notice either. If nothing arrives for this
# long, force-close and reconnect rather than hang indefinitely.
FRAME_SILENCE_TIMEOUT = 30  # seconds

# Device online/offline comes from GET user_device/list's "state" field
# (true/false), not from the WS telemetry stream, so it's polled separately
# on a timer rather than derived from coordinator.data.
DEVICE_STATUS_POLL_INTERVAL = 60  # seconds

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

# --- Control command format ------------------------------------------------
# Reverse-engineered from six captured (tag, value) -> cmd hex pairs (AC/DC/
# USB, each on and off). All six reproduce byte-for-byte with this formula:
#   cmd = CTRL_COMMAND_PREFIX + tag(2B LE, hex) + value(4B LE, hex)
#         + crc16_modbus(tag_bytes + value_bytes) as 2 bytes, BIG-endian
# CRC is CRC16/MODBUS (poly 0xA001, init 0xFFFF) computed over just the
# 6-byte [tag+value] portion - NOT including this prefix. See api.py's
# build_control_command() for the implementation.
CTRL_COMMAND_PREFIX = "0e000c000800"

# --- TLV tags -------------------------------------------------------------
# Re-derived from real live captures (custom_components.fossibot_plus debug
# log) cross-checked against the FOSSiBOT+ app screen at the same moment
# (2026-09-26/27), plus - for the AC/DC/USB tags - against six captured
# control-command requests that write these exact same tags. The original
# source spec's tag table turned out to be wrong or incomplete in several
# places - see README.md/DEVELOPMENT.md for the full reasoning.

# CONFIRMED - both by matching the app's readout AND (for AC/DC/USB) by the
# control command that writes this exact tag:
TAG_BATTERY_SOC = "0100"          # battery %, matches app's SOC readout exactly
TAG_TEMPERATURE = "0200"          # deg C, matches the single dial-icon temperature
TAG_REMAINING_MINUTES = "0300"    # minutes until full/empty. The source spec called
                                   # this "AC input power" - wrong. Matched exactly
                                   # to the app's "X год Y хв" readout across three
                                   # separate captures (4020, 765, and 3840 minutes).
TAG_AC_FREQUENCY = "1600"         # raw / 10 = Hz. AC on -> ~500 (50.0Hz), AC off -> 0
TAG_OUTPUT_POWER = "1400"         # Watts. Source spec called this "inverter
                                   # temperature" - wrong. Confirmed by TWO
                                   # independent live samples matching the app's
                                   # output-power readout to the exact watt:
                                   # 11 -> 11W, and later 10 -> 10W.
TAG_AC_STATE = "2700"             # AC output on/off (0/1). The source spec called
                                   # this "main power state" - also wrong. This is
                                   # the exact tag the control command writes to
                                   # toggle AC (confirmed by replaying the captured
                                   # cmd hex byte-for-byte), and it matches the
                                   # app's AC toggle in telemetry in every capture.
TAG_DC_STATE = "2800"             # DC output on/off (0/1) - confirmed the same way
                                   # as TAG_AC_STATE (control command's exact tag),
                                   # and matches the app's DC toggle in every capture.
TAG_USB_STATE = "2900"            # USB output on/off (0/1) - confirmed the same way
                                   # as TAG_AC_STATE, matches the app's USB toggle
                                   # (only ever observed while off, but the control
                                   # tag match itself is solid evidence).

# MIRRORS - identical to a confirmed tag in every frame observed so far;
# kept as separate raw diagnostics in case they ever diverge:
TAG_OUTPUT_POWER_MIRROR = "2300"  # == TAG_OUTPUT_POWER in every frame so far
                                   # (source spec called this "battery temperature").
TAG_AC_STATE_MIRROR = "2b00"      # == TAG_AC_STATE in every frame so far. This was
                                   # the tag I originally (wrongly) treated as THE
                                   # AC-state tag before the control-command capture
                                   # revealed 2700 is the one the app actually writes.

# CANDIDATES - plausible but not yet fully confirmed:
TAG_CHARGING_ACTIVE_CANDIDATE = "0400"  # 0 in every idle/output-only capture so
                                     # far, 1 throughout a live AC-charging
                                     # capture - decent binary correlation, but
                                     # only tested across two distinct states.
TAG_INPUT_POWER_CANDIDATE = "1300"  # Direct watts (scale 1:1). Confirmed by a
                                     # full AC-charging session: ramped from ~262W
                                     # on plug-in to 398-402W at steady state,
                                     # matching the app's "~400W" input load. Never
                                     # nonzero at the same time as 1400 (output),
                                     # which makes sense (in vs out). Still labeled
                                     # "candidate" because the exact app wattage was
                                     # eyeballed ("~400W") rather than read off the
                                     # screen at the precise same instant as the log
                                     # frame - but the correlation is very tight.
TAG_INPUT_POWER_MIRROR_CANDIDATE = "2200"  # == TAG_INPUT_POWER_CANDIDATE in every
                                     # frame so far, same relationship as the
                                     # 1400/2300 output-power mirror pair.
TAG_BATTERY_VOLTAGE_CANDIDATE = "1500"  # raw * 0.01 = V. ~23.1V at 64-67% SOC
                                     # (idle), but ~22.9-23.0V at 77% SOC while
                                     # charging - LOWER at higher SOC, which is
                                     # backwards for a simple resting pack
                                     # voltage. Could still be right if this is
                                     # terminal voltage under charge current
                                     # rather than open-circuit voltage, but
                                     # that's an extra assumption - treat with
                                     # more caution than the other candidates.

# UNCONFIRMED / likely wrong as originally documented - kept only as raw
# diagnostics, disabled by default in sensor.py:
TAG_BATTERY_PACK = "0500"         # NOT actually two packed 16-bit sub-values as
                                   # previously assumed - that was a misreading on
                                   # my part. The real frame has a separate,
                                   # currently-unmapped tag "1200" right after it;
                                   # 0500's own raw uint32 value has no known
                                   # physical meaning yet. Exposed raw, unconfirmed.
TAG_UNKNOWN_2C00 = "2c00"         # NOT the DC on/off flag (that's confirmed to be
                                   # TAG_DC_STATE/2800 - see above): stayed at raw
                                   # value 2 regardless of DC state in every
                                   # capture. Likely unrelated (e.g. a port count
                                   # or mode setting), meaning still unknown.
TAG_UNKNOWN_2D00 = "2d00"         # same situation as TAG_UNKNOWN_2C00, for what
                                   # was previously (wrongly) assumed to be USB.
TAG_INPUT_VOLTAGE = "2a00"        # Was constant 400 across two non-charging
                                   # captures, but dropped to 200 once AC charging
                                   # started in a later capture - so NOT static
                                   # after all, contrary to the earlier note here.
                                   # Clearly related to charging somehow, but its
                                   # exact physical meaning and scale are still
                                   # unknown - kept raw, unconfirmed.

