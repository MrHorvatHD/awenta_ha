import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class AwentaCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, api):

        super().__init__(
            hass,
            _LOGGER,
            name="awenta",
            update_interval=None,
        )

        self.api = api
        self.data = {}

        self.api.register_listener(self._handle_update)
        self.api.register_status_listener(self.async_update_listeners)

    def _handle_update(self, mac, data):

        self.data[mac] = data

        self.async_set_updated_data(self.data)