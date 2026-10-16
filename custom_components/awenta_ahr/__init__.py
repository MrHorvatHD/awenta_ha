import logging

from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .awenta_api import AwentaAPI
from .coordinator import AwentaCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):

    hass.data.setdefault(DOMAIN, {})

    email = entry.data["email"]
    password = entry.data["password"]

    api = AwentaAPI(hass, email, password)

    try:
        await api.start()
    except Exception as err:  # cloud unreachable, wrong login or unexpected answer → HA retries later
        await api.stop()
        raise ConfigEntryNotReady(f"Awenta cloud not available: {err}") from err

    coordinator = AwentaCoordinator(hass, api)

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass, entry):

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api"].stop()

    return unload_ok