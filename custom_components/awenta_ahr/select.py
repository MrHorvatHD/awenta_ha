from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .entity import AwentaEntity
from .const import (
    DOMAIN,
    HYGROSTAT_OPTIONS,
    OPTION_HYGROSTAT,
    OPTION_TIMER,
    TIMER_OPTIONS,
)


MODE_MAP = {
    "Recuperation": 2,
    "Supply": 1,
    "Extract": 0,
}

MODE_MAP_REV = {v: k for k, v in MODE_MAP.items()}


async def async_setup_entry(hass, entry, async_add_entities):

    data = hass.data[DOMAIN][entry.entry_id]

    api = data["api"]
    coordinator = data["coordinator"]

    entities = []

    for device in api.devices:

        entities.append(
            AwentaModeSelect(coordinator, api, device["mac"], device["name"])
        )
        entities.append(
            AwentaHygrostatSelect(coordinator, api, device["mac"], device["name"])
        )
        entities.append(
            AwentaTimerSelect(coordinator, api, device["mac"], device["name"])
        )

    async_add_entities(entities)


class AwentaModeSelect(AwentaEntity, SelectEntity):

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Mode"
        self._attr_unique_id = f"{mac}_mode"
        self._attr_options = list(MODE_MAP.keys())

    @property
    def current_option(self):

        mode = self.coordinator.data.get(self.mac, {}).get("mode")

        return MODE_MAP_REV.get(mode)

    async def async_select_option(self, option):

        await self.api.send(
            self.mac,
            {
                "act": "send_work_mode",
                "mode_nr": MODE_MAP[option],
            },
        )


class _ExtraOptionSelect(AwentaEntity, SelectEntity):
    """Hygrostat and timer are extra operating options: only one is active at a time and the unit ignores them while
    switched off (the official app hides them then), so setting one while the unit is off fails with an explanation."""

    _what = ""

    @property
    def _data(self):

        return self.coordinator.data.get(self.mac, {})

    def _require_running(self):

        if not self._data.get("power", False):
            raise HomeAssistantError(
                f"{self.device_name} must be running to set the {self._what} (the unit ignores it while it is off)"
            )


class AwentaHygrostatSelect(_ExtraOptionSelect):
    """Humidity threshold: above it the unit runs at the highest gear, below it it idles (gear 0)."""

    _what = "hygrostat"
    _attr_icon = "mdi:water-percent"

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Hygrostat"
        self._attr_unique_id = f"{mac}_hygrostat"
        self._attr_options = HYGROSTAT_OPTIONS

    @property
    def current_option(self):

        data = self._data

        if data.get("option") != OPTION_HYGROSTAT:
            return HYGROSTAT_OPTIONS[0]

        level = data.get("ht_level", 0)

        return HYGROSTAT_OPTIONS[level] if 0 <= level < len(HYGROSTAT_OPTIONS) else HYGROSTAT_OPTIONS[0]

    async def async_select_option(self, option):

        self._require_running()

        await self.api.send(
            self.mac,
            {"act": "send_higro_level", "level": HYGROSTAT_OPTIONS.index(option)},
        )


class AwentaTimerSelect(_ExtraOptionSelect):
    """Run for the chosen time, then the unit switches itself off."""

    _what = "timer"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Timer"
        self._attr_unique_id = f"{mac}_timer"
        self._attr_options = TIMER_OPTIONS

    @property
    def current_option(self):

        data = self._data

        # timer_level stays at its last value after the timer ran out; only an active timer counts
        if data.get("option") != OPTION_TIMER:
            return TIMER_OPTIONS[0]

        level = data.get("timer_level", 0)

        return TIMER_OPTIONS[level] if 0 <= level < len(TIMER_OPTIONS) else TIMER_OPTIONS[0]

    async def async_select_option(self, option):

        self._require_running()

        await self.api.send(
            self.mac,
            {"act": "send_timer_level", "level": TIMER_OPTIONS.index(option)},
        )
