"""Local control: Home Assistant itself is the server the units connect to (same interface as AwentaAPI)."""
import logging
import ssl

from homeassistant.exceptions import HomeAssistantError

from . import frames
from .cert import ensure_certificate
from .unit_server import UnitServer

_LOGGER = logging.getLogger(__name__)


def _make_context(cert_path, key_path):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert_path, key_path)
    return ctx


class AwentaLocalAPI:

    def __init__(self, hass, port, devices, directory, on_new_device):

        self.hass = hass
        self.port = port
        self.directory = directory
        self._on_new_device = on_new_device

        self.devices = [{"mac": mac, "name": name} for mac, name in devices.items()]
        self.listeners = []
        self.status_listeners = []
        self._server = None

    def register_listener(self, callback):
        self.listeners.append(callback)

    def register_status_listener(self, callback):
        self.status_listeners.append(callback)

    async def start(self):

        cert_path, key_path = await self.hass.async_add_executor_job(ensure_certificate, self.directory)
        context = await self.hass.async_add_executor_job(_make_context, cert_path, key_path)

        self._server = UnitServer(self.port, context, self._report, self._connected, self._disconnected)
        await self._server.start()

    async def stop(self):

        if self._server is not None:
            await self._server.stop()
            self._server = None

    def online(self, mac):

        return self._server is not None and self._server.online(mac)

    async def send(self, mac, payload):

        if self._server is None or not self._server.online(mac):
            # Fail loudly: a silently dropped command would leave callers out of sync.
            raise HomeAssistantError(f"Awenta unit {mac} is not connected to Home Assistant")

        try:
            payloads = frames.command_payloads(payload, self._server.timezone(mac))
        except (ValueError, KeyError) as err:
            raise HomeAssistantError(f"Awenta unit {mac}: {err}") from err

        try:
            await self._server.send(mac, payloads)
        except (ConnectionError, OSError) as err:
            raise HomeAssistantError(f"Awenta unit {mac}: sending failed: {err}") from err

    # -- callbacks from the unit server (run in Home Assistant's event loop) ------------------------------------

    def _report(self, mac, state):

        for callback in self.listeners:
            callback(mac, state)

    def _connected(self, mac):

        _LOGGER.info("Awenta unit %s connected", mac)

        if not any(device["mac"] == mac for device in self.devices):
            name = f"Awenta {mac[-5:].replace(':', '')}"
            self.devices.append({"mac": mac, "name": name})
            self._on_new_device(mac, name)

        self._notify_status()

    def _disconnected(self, mac):

        _LOGGER.info("Awenta unit %s disconnected", mac)
        self._notify_status()

    def _notify_status(self):

        for callback in self.status_listeners:
            callback()
