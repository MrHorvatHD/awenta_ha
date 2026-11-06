from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

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
        entities.append(
            AwentaFilterResetButton(coordinator, api, device["mac"], device["name"])
        )

    async_add_entities(entities)


class AwentaDisplayButton(AwentaEntity, ButtonEntity):
    """One press of the unit's DISP button.

    The unit cycles its display on every press
    (dimmed → humidity → temperature → clock → automatic → dimmed …) and does not report which screen is shown,
    so callers have to track the position themselves.
    """

    _attr_icon = "mdi:monitor"

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Display"
        self._attr_unique_id = f"{mac}_display"

    async def async_press(self):

        await self.api.send(self.mac, {"act": "set_display"})



class AwentaFilterResetButton(AwentaEntity, ButtonEntity):
    """Reset the filter-hours counter to its full value (2160 h) after a filter change.

    The unit ignores the reset command while it is switched off (the official app hides the option then), so
    pressing the button while the unit is off fails with an explanation instead of silently doing nothing. The
    button itself stays available so a dashboard can show the hours left and explain why a reset is not possible.
    """

    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Filter reset"
        self._attr_unique_id = f"{mac}_filter_reset"

    @property
    def _running(self):

        return bool(self.coordinator.data.get(self.mac, {}).get("power", False))

    async def async_press(self):

        if not self._running:
            raise HomeAssistantError(
                f"{self.device_name} must be running to reset the filter (the unit ignores the reset while it is off)"
            )

        await self.api.send(self.mac, {"act": "set_filter_reset"})
