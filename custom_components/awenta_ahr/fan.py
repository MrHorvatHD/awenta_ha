import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .entity import AwentaEntity
from .const import DOMAIN

SPEED_RANGE = (1, 3)


async def async_setup_entry(hass, entry, async_add_entities):

    data = hass.data[DOMAIN][entry.entry_id]

    api = data["api"]
    coordinator = data["coordinator"]

    entities = []

    for device in api.devices:

        entities.append(
            AwentaFan(coordinator, api, device["mac"], device["name"])
        )

    async_add_entities(entities)


class AwentaFan(AwentaEntity, FanEntity):

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = name
        self._attr_unique_id = f"{mac}_fan"
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )
        self._attr_speed_count = 3

    @property
    def _data(self):

        return self.coordinator.data.get(self.mac, {})

    @property
    def is_on(self):

        return bool(self._data.get("power", False))

    @property
    def percentage(self):

        gear = self._data.get("recuperation_gear_adv", 0)

        if not self.is_on or not gear:
            return 0

        return ranged_value_to_percentage(SPEED_RANGE, gear)

    async def _send_gear(self, percentage):

        gear = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))

        await self.api.send(
            self.mac,
            {
                "act": "send_gear_number",
                "gear_nr": max(1, min(3, gear)),
            },
        )

    async def async_set_percentage(self, percentage):

        if percentage == 0:
            await self.async_turn_off()
            return

        if not self.is_on:
            await self.api.send(self.mac, {"act": "send_power_on"})

        await self._send_gear(percentage)

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):

        if percentage == 0:
            await self.async_turn_off()
            return

        await self.api.send(self.mac, {"act": "send_power_on"})

        if percentage is not None:
            await self._send_gear(percentage)

    async def async_turn_off(self, **kwargs):

        await self.api.send(self.mac, {"act": "send_power_off"})
