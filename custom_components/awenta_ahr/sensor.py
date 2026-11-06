from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime, PERCENTAGE

from .entity import AwentaEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):

    data = hass.data[DOMAIN][entry.entry_id]

    api = data["api"]
    coordinator = data["coordinator"]

    entities = []

    for device in api.devices:

        mac = device["mac"]
        name = device["name"]

        entities.append(
            AwentaTemperatureSensor(coordinator, api, mac, name)
        )

        entities.append(
            AwentaHumiditySensor(coordinator, api, mac, name)
        )

        entities.append(
            AwentaFilterSensor(coordinator, api, mac, name)
        )

        entities.append(
            AwentaTimerLeftSensor(coordinator, api, mac, name)
        )

    async_add_entities(entities)


class AwentaTemperatureSensor(AwentaEntity, SensorEntity):

    # a measurement state class makes Home Assistant keep long-term (hourly) statistics, not just 10 days of history
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Temperature"
        self._attr_unique_id = f"{mac}_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):

        data = self.coordinator.data.get(self.mac, {})

        if data.get("valid_sensor"):
            return data.get("temperature_sensor", 0) / 10

        return None


class AwentaHumiditySensor(AwentaEntity, SensorEntity):

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Humidity"
        self._attr_unique_id = f"{mac}_humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):

        data = self.coordinator.data.get(self.mac, {})

        if data.get("valid_sensor"):
            return data.get("humidity_sensor", 0) / 10

        return None


class AwentaFilterSensor(AwentaEntity, SensorEntity):
    """Hours left until the filter must be replaced (2160 after a reset)."""

    _attr_icon = "mdi:air-filter"
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Filter hours left"
        self._attr_unique_id = f"{mac}_filter_hours_left"

    @property
    def native_value(self):

        data = self.coordinator.data.get(self.mac, {})

        return data.get("time_filter_time_left")


class AwentaTimerLeftSensor(AwentaEntity, SensorEntity):
    """Minutes left on the timer (0 when no timer is running)."""

    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator, api, mac, name)

        self._attr_name = f"{name} Timer left"
        self._attr_unique_id = f"{mac}_timer_left"

    @property
    def native_value(self):

        data = self.coordinator.data.get(self.mac, {})

        return data.get("timer_left")
