"""REST + WebSocket client for the FOSSiBOT cloud (app.fossibot.hk).

The account login/device-list calls are plain REST. Live telemetry comes
over a WebSocket that the server closes after ~15s of silence, so a
{"type": "hear", "msg": "<email>"} heartbeat frame must be sent every
5 seconds. Each device (snCode) needs its own WS connection.
"""
from __future__ import annotations

import asyncio
import json
import logging
import struct
from typing import Callable

import aiohttp

from .const import (
    DEVICE_LIST_ENDPOINT,
    HEARTBEAT_INTERVAL,
    LOGIN_ENDPOINT,
    RECONNECT_DELAY,
    WS_URL,
)

_LOGGER = logging.getLogger(__name__)

_COMMON_HEADERS = {
    "lang": "uk",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 16; SM-A536E Build/BP2A.250605.031.A3; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/153.0.8010.36 "
        "Mobile Safari/537.36 uni-app (Immersed/33.142857) Html5Plus/1.0"
    ),
}

HEADER_LEN = 6  # bytes
TAIL_LEN = 2    # bytes - CRC16, parsed but NOT validated: the source spec
                # never documented the checksum algorithm.
BLOCK_LEN = 6   # bytes per [tag(2)][value(4, little-endian)] block


class FossibotAuthError(Exception):
    """Email/password rejected by the API."""


class FossibotConnectionError(Exception):
    """Network or unexpected-API-response failure."""


def parse_payload(hex_str: str) -> dict[str, int]:
    """Decode one TLV telemetry frame into {tag_hex: raw_uint32}.

    Layout: 6-byte header, then repeating 6-byte
    [2-byte tag][4-byte little-endian value] blocks, then a 2-byte tail.
    Most tags are a single uint32 counter/flag; a few (see const.py,
    e.g. TAG_BATTERY_PACK) actually pack two 16-bit sub-values into that
    same 4-byte slot - callers that need those must split the raw value
    themselves (low word = value & 0xFFFF, high word = value >> 16).
    """
    raw = bytes.fromhex(hex_str)
    body = raw[HEADER_LEN:-TAIL_LEN]
    usable = len(body) - (len(body) % BLOCK_LEN)
    metrics: dict[str, int] = {}
    for offset in range(0, usable, BLOCK_LEN):
        block = body[offset : offset + BLOCK_LEN]
        tag = block[0:2].hex()
        value = struct.unpack("<I", block[2:6])[0]
        metrics[tag] = value
    return metrics


class FossibotApiClient:
    """Login + device discovery over the REST API."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self.session = session
        self.email = email
        self.password = password
        self.token: str | None = None

    async def async_login(self) -> str:
        headers = {**_COMMON_HEADERS, "Content-Type": "application/json"}
        payload = {"username": self.email, "password": self.password}
        try:
            async with self.session.post(LOGIN_ENDPOINT, json=payload, headers=headers) as resp:
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise FossibotConnectionError(str(err)) from err

        if data.get("code") != 200 or not data.get("token"):
            raise FossibotAuthError(data.get("msg", "login failed"))

        self.token = data["token"]
        return self.token

    async def async_get_devices(self, *, _retried: bool = False) -> list[dict]:
        if not self.token:
            await self.async_login()
        headers = {**_COMMON_HEADERS, "Authorization": f"Bearer {self.token}"}
        try:
            async with self.session.get(
                DEVICE_LIST_ENDPOINT,
                params={"pageNum": 1, "pageSize": 50},
                headers=headers,
            ) as resp:
                if resp.status == 401 and not _retried:
                    # Token expired - the source spec never covers refresh,
                    # so just re-login once and retry.
                    await self.async_login()
                    return await self.async_get_devices(_retried=True)
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise FossibotConnectionError(str(err)) from err

        if data.get("code") != 200:
            raise FossibotConnectionError(data.get("msg", "device list failed"))
        return data.get("rows", [])


class FossibotWebSocket:
    """One persistent WSS telemetry channel for a single device (snCode).

    The original spec only described the happy path (connect, heartbeat
    every 5s). It said nothing about what to do if the socket drops, so
    this adds a reconnect loop with a fixed backoff.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api: FossibotApiClient,
        sn_code: str,
        on_data: Callable[[dict[str, int]], None],
    ) -> None:
        self._session = session
        self._api = api
        self._sn_code = sn_code
        self._on_data = on_data
        self._heartbeat_task: asyncio.Task | None = None
        self._listen_task: asyncio.Task | None = None
        self._stopped = False

    async def async_start(self) -> None:
        self._stopped = False
        self._listen_task = asyncio.create_task(self._run())

    async def async_stop(self) -> None:
        self._stopped = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listen_task:
            self._listen_task.cancel()

    async def _run(self) -> None:
        while not self._stopped:
            try:
                await self._connect_and_listen()
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("FOSSiBOT WS %s dropped: %s", self._sn_code, err)
            if self._stopped:
                break
            await asyncio.sleep(RECONNECT_DELAY)

    async def _connect_and_listen(self) -> None:
        headers = {
            **_COMMON_HEADERS,
            "Authorization": f"Bearer {self._api.token}",
            "snCode": self._sn_code,
            "Origin": "http://localhost",
            "User-Agent": "okhttp/3.12.11",
        }
        async with self._session.ws_connect(WS_URL, headers=headers, heartbeat=None) as ws:
            self._heartbeat_task = asyncio.create_task(self._send_heartbeat(ws))
            try:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self._handle_frame(msg.data)
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                        aiohttp.WSMsgType.CLOSE,
                    ):
                        break
            finally:
                self._heartbeat_task.cancel()

    async def _send_heartbeat(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        payload = {"type": "hear", "msg": self._api.email}
        try:
            while not ws.closed:
                await ws.send_json(payload)
                await asyncio.sleep(HEARTBEAT_INTERVAL)
        except asyncio.CancelledError:
            pass
        except aiohttp.ClientError as err:
            _LOGGER.debug("Heartbeat send failed for %s: %s", self._sn_code, err)

    def _handle_frame(self, raw: str) -> None:
        try:
            envelope = json.loads(raw)
            metrics = parse_payload(envelope["data"])
        except (ValueError, KeyError, IndexError) as err:
            _LOGGER.debug("Ignoring unparsable frame from %s: %s", self._sn_code, err)
            return
        self._on_data(metrics)
