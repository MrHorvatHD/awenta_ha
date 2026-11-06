import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_DEVICES, CONF_MODE, CONF_PORT, DEFAULT_PORT, DOMAIN, MODE_CLOUD, MODE_LOCAL


CLOUD_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)

LOCAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
    }
)


def _settings(entry):

    mode = entry.options.get(CONF_MODE, entry.data.get(CONF_MODE, MODE_CLOUD))
    port = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT))

    return mode, port


class AwentaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):

        return self.async_show_menu(step_id="user", menu_options=[MODE_LOCAL, MODE_CLOUD])

    async def async_step_local(self, user_input=None):

        if user_input is not None:

            await self.async_set_unique_id(MODE_LOCAL)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Awenta HRV (local)",
                data={CONF_MODE: MODE_LOCAL, CONF_PORT: user_input[CONF_PORT], CONF_DEVICES: {}},
            )

        return self.async_show_form(step_id="local", data_schema=LOCAL_SCHEMA)

    async def async_step_cloud(self, user_input=None):

        if user_input is not None:

            await self.async_set_unique_id(user_input["email"])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Awenta HRV",
                data={CONF_MODE: MODE_CLOUD, **user_input},
            )

        return self.async_show_form(step_id="cloud", data_schema=CLOUD_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):

        return AwentaOptionsFlow()


class AwentaOptionsFlow(config_entries.OptionsFlow):
    """Switch between local and cloud mode, change the port and rename the units."""

    async def async_step_init(self, user_input=None):

        entry = self.config_entry
        mode, port = _settings(entry)
        devices = entry.data.get(CONF_DEVICES, {})
        errors = {}

        if user_input is not None:

            if user_input[CONF_MODE] == MODE_CLOUD and "email" not in entry.data:
                errors[CONF_MODE] = "cloud_needs_account"
            else:
                names = {mac: user_input.get(f"name_{mac}", name) for mac, name in devices.items()}
                if names != devices:
                    self.hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_DEVICES: names})
                return self.async_create_entry(
                    title="",
                    data={CONF_MODE: user_input[CONF_MODE], CONF_PORT: user_input[CONF_PORT]},
                )

        schema = {
            vol.Required(CONF_MODE, default=mode): vol.In([MODE_LOCAL, MODE_CLOUD]),
            vol.Required(CONF_PORT, default=port): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
        }
        for mac, name in devices.items():
            schema[vol.Optional(f"name_{mac}", default=name)] = str

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema), errors=errors)
