import logging

from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import CONF_DEVICES, CONF_MODE, CONF_PORT, DEFAULT_PORT, DOMAIN, MODE_CLOUD, MODE_LOCAL, PLATFORMS
from .awenta_api import AwentaAPI
from .coordinator import AwentaCoordinator
from .local_api import AwentaLocalAPI

_LOGGER = logging.getLogger(__name__)


def get_settings(entry):
    """(mode, port): options win over the data the entry was created with. Entries from v1.x are cloud entries."""

    mode = entry.options.get(CONF_MODE, entry.data.get(CONF_MODE, MODE_CLOUD))
    port = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT))

    return mode, port


def _snapshot(entry):

    mode, port = get_settings(entry)

    return (mode, port, tuple(sorted(entry.data.get(CONF_DEVICES, {}).items())))


async def async_setup_entry(hass, entry):

    hass.data.setdefault(DOMAIN, {})

    mode, port = get_settings(entry)

    if mode == MODE_LOCAL:

        def on_new_device(mac, name):
            """A unit we have not seen before connected: remember it and reload so its entities get created."""
            devices = dict(entry.data.get(CONF_DEVICES, {}))
            devices[mac] = name
            stored = hass.data.get(DOMAIN, {}).get(entry.entry_id)
            if stored is not None:
                stored["snapshot"] = (mode, port, tuple(sorted(devices.items())))  # one explicit reload, not two
            hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_DEVICES: devices})
            hass.config_entries.async_schedule_reload(entry.entry_id)

        api = AwentaLocalAPI(
            hass,
            port,
            dict(entry.data.get(CONF_DEVICES, {})),
            hass.config.path(".storage"),
            on_new_device,
        )

        try:
            await api.start()
        except Exception as err:  # e.g. the port is already in use → HA retries later
            await api.stop()
            raise ConfigEntryNotReady(f"Awenta unit server could not start on port {port}: {err}") from err

    else:

        if "email" not in entry.data or "password" not in entry.data:
            raise ConfigEntryError("Cloud mode needs an Awenta account; configure it or switch to local mode")

        api = AwentaAPI(hass, entry.data["email"], entry.data["password"])

        try:
            await api.start()
        except Exception as err:  # cloud unreachable, wrong login or unexpected answer → HA retries later
            await api.stop()
            raise ConfigEntryNotReady(f"Awenta cloud not available: {err}") from err

    coordinator = AwentaCoordinator(hass, api)

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "snapshot": _snapshot(entry),
    }

    if mode == MODE_CLOUD:
        # Remember the unit names so local mode can keep the same entity names after switching.
        names = {device["mac"]: device["name"] for device in api.devices}
        if names and names != entry.data.get(CONF_DEVICES):
            data = {**entry.data, CONF_DEVICES: names}
            hass.data[DOMAIN][entry.entry_id]["snapshot"] = (mode, port, tuple(sorted(names.items())))
            hass.config_entries.async_update_entry(entry, data=data)

    entry.async_on_unload(entry.add_update_listener(_entry_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _entry_updated(hass, entry):
    """Reload when the connection mode, port or unit names changed (not for our own bookkeeping updates)."""

    stored = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    if stored is None or stored["snapshot"] == _snapshot(entry):
        return

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api"].stop()

    return unload_ok
