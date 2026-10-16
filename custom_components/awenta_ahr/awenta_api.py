import asyncio
import websockets
import hashlib
import json
import urllib.parse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.ssl import get_default_context

from .const import API_URL, WS_URL


class AwentaAPI:

    def __init__(self, hass, email, password):

        self.hass = hass
        self.email = email
        self.password = password

        self.sha1 = None
        self.id_socket = None
        self.key_socket = None

        self.devices = []
        self.listeners = []
        self.ws = {}
        self._tasks = []

    def register_listener(self, callback):
        self.listeners.append(callback)

    async def start(self):

        await self.login()
        await self.list_devices()

        for device in self.devices:
            self._tasks.append(
                self.hass.async_create_background_task(
                    self.websocket_loop(device["mac"]),
                    f"awenta_ahr websocket {device['mac']}",
                )
            )

    async def stop(self):
        """Stop the websocket loops and close their connections (unload / reload)."""
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._tasks.clear()
        for ws in list(self.ws.values()):
            try:
                await ws.close()
            except Exception:
                pass
        self.ws.clear()

    async def login(self):

        self.sha1 = hashlib.sha1(self.password.encode()).hexdigest()

        payload = {
            "action": "version",
            "authorization": {
                "email": self.email,
                "pass": self.sha1,
                "lang": "pl",
            },
            "params": json.dumps({"model": "HA"}),
        }

        data = {"data": json.dumps(payload)}

        session = async_get_clientsession(self.hass)
        async with session.post(
            API_URL,
            data=urllib.parse.urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            result = await resp.text()

        j = json.loads(result)
        if not isinstance(j.get("params"), dict) or "id" not in j["params"]:
            raise RuntimeError(f"unexpected login answer from the Awenta cloud: {result[:200]}")

        self.id_socket = j["params"]["id"]
        self.key_socket = j["params"]["key"]

    async def list_devices(self):

        payload = {
            "action": "list_devices",
            "authorization": {
                "email": self.email,
                "pass": self.sha1,
                "lang": "pl",
            },
            "params": "{}",
        }

        data = {"data": json.dumps(payload)}

        session = async_get_clientsession(self.hass)
        async with session.post(
            API_URL,
            data=urllib.parse.urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            result = await resp.text()

        j = json.loads(result)
        if not isinstance(j.get("params"), list):
            raise RuntimeError(f"unexpected device list from the Awenta cloud: {result[:200]}")

        self.devices = j["params"]

    async def websocket_loop(self, mac):

        while True:

            try:

                ws = await websockets.connect(
                    WS_URL,
                    ssl=get_default_context(),
                    additional_headers={"source": "android"},
                )

                self.ws[mac] = ws

                join = {
                    "act": "join",
                    "id": self.id_socket,
                    "key": self.key_socket,
                    "mac": mac,
                }

                await ws.send(json.dumps(join))

                while True:

                    msg = await ws.recv()
                    data = json.loads(msg)

                    for callback in self.listeners:
                        callback(mac, data)

            except Exception:

                ws = self.ws.pop(mac, None)
                if ws is not None:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                await asyncio.sleep(5)

    async def send(self, mac, payload):

        ws = self.ws.get(mac)

        if not ws:
            # Fail loudly: a silently dropped command (e.g. a display press) would leave callers out of sync.
            raise HomeAssistantError(f"Awenta unit {mac} is not connected to the cloud")

        payload["id"] = self.id_socket
        payload["key"] = self.key_socket
        payload["mac"] = mac

        try:
            await ws.send(json.dumps(payload))
        except Exception as err:
            raise HomeAssistantError(f"Awenta unit {mac}: sending failed: {err}") from err