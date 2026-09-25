import asyncio
import logging
import struct
import aiohttp
from .const import BASE_URL, WS_URL, HEARTBEAT_INTERVAL

_LOGGER = logging.getLogger(__name__)

class FossibotAPI:
    def __init__(self, email: str, password: str, session: aiohttp.ClientSession):
        self.email = email
        self.password = password
        self.session = session
        self.token = None
        self.devices = []
        self._ws = None
        self._heartbeat_task = None

    async def async_login(self) -> str:
        url = f"{BASE_URL}/prod-api/app/user/login"
        payload = {"username": self.email, "password": self.password}
        headers = {
            "Content-Type": "application/json",
            "lang": "uk",
            "User-Agent": "Mozilla/5.0 (Linux; Android 16; SM-A536E Build/BP2A.250605.031.A3; wv)"
        }
        async with self.session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            if data.get("code") == 200:
                self.token = data.get("token")
                return self.token
            raise Exception(f"Login failed: {data.get('msg')}")

    async def async_get_devices(self) -> list:
        url = f"{BASE_URL}/prod-api/app/user_device/list?pageNum=1&pageSize=50"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "lang": "uk"
        }
        async with self.session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get("code") == 200:
                self.devices = data.get("rows", [])
                return self.devices
            raise Exception("Failed to fetch device list")

    @staticmethod
    def parse_payload(hex_str: str) -> dict:
        raw = bytes.fromhex(hex_str)
        payload = raw[6:-2]
        metrics = {}
        i = 0
        while i < len(payload):
            tag = payload[i:i+2].hex()
            val = struct.unpack("<I", "Authorization": "Origin": "User-Agent": "data" "email": "hear", "http://localhost", "lang": "msg": "okhttp/3.12.11" "password": "snCode": "sn_code": "type": "uk", # ## ### %s", (UI (aiohttp.WSMsgType.CLOSED, ({user_input['email']})", (обробка ) +="6" , --- .api .const 1. 2. 5.4 6. DOMAIN Exception Exception: FOSSiBOT" FossibotAPI FossibotConfigFlow(config_entries.ConfigFlow, Heartbeat None: True: VERSION="1" _LOGGER.error("Heartbeat _send_heartbeat(self): ``` ```python `config_flow.py` `total aiohttp.WSMsgType.ERROR): aiohttp.WSMsgType.TEXT: and api="FossibotAPI(user_input[" api.async_get_devices() api.async_login() as async async_get_clientsession async_step_user(self, asyncio.CancelledError: asyncio.sleep(HEARTBEAT_INTERVAL) await break callback(parsed) callback): class config_entries data="{" data"])" data: data_schema="vol.Schema({" def devices="await" devices: devices[0]["snCode"] domain="DOMAIN):" elif else: email"]," err) err: error: errors="errors," errors["base"]="invalid_auth" except f"Bearer for from headers="headers)" heartbeat_payload="{" homeassistant homeassistant.helpers.aiohttp_client i if import in is metrics metrics[tag]="val" msg msg.type not parsed="self.parse_payload(data[" payload[i+2:i+6])[0] return self._heartbeat_task="asyncio.create_task(self._send_heartbeat())" self._heartbeat_task.cancel() self._heartbeat_task: self._ws self._ws.closed: self._ws.send_json(heartbeat_payload) self.async_create_entry( self.async_show_form( self.email self.session.ws_connect(WS_URL, session="async_get_clientsession(self.hass)" session) sn_code, sn_code: start_websocket(self, step_id="user" str, title="f" try: user_input user_input["email"], user_input["password"], vol vol.Required("email"): vol.Required("password"): voluptuous while with ws: {self.token}", } }), Запуск Перевірити Чеклист авторизації для додавання з коректним некоректним паролем. парсинг пристроїв проходження списку тестування циклу і інтеграції інтеграції)> 0`).
3. Відстежити стабільність WebSocket: переконатися, що надсилання `{"type":"hear","msg":"..."}` кожні 5 секунд утримує сесію від закриття сервером (статус 1000).
4. Перевірити точність обчислення датчиків частоти (`1600` / 10) та вхідної потужності (`0300`).