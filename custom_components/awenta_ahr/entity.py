from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL


class AwentaEntity(CoordinatorEntity):

    def __init__(self, coordinator, api, mac, name):

        super().__init__(coordinator)

        self.api = api
        self.mac = mac
        self.device_name = name

    @property
    def available(self):

        return super().available and self.api.online(self.mac)

    @property
    def device_info(self):

        return DeviceInfo(
            identifiers={(DOMAIN, self.mac)},
            name=self.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("mac", self.mac)},
        )