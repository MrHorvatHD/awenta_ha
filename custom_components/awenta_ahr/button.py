from homeassistant.components.button import ButtonEntity

from .entity import AwentaEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):

    data = hass.data[DOMAIN][entry.entry_id]

    api = data["api"]
    coordinator = data["coordinator"]

    entities = []

    for device in api.devices:

        entities.append(
            AwentaDisplayButton(coordinator, api, device["mac"], device["name"])
        )

    async_add_entities(entities)


class AwentaDisplayButton(AwentaEntity, ButtonEntity):
    """One press of the unit's DISP button.

    The unit cycles its display on every press (dimmed → humidity → temperature → clock → automatic → dimmed …)
    and does not report which screen is shown, so callers have to track the position themselves.
    """

    _attr_icon = "mdi:monitor"

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Display"
        self._attr_unique_id = f"{mac}_display"

    async def async_press(self):

        await self.api.send(self.mac, {"act": "set_display"})
