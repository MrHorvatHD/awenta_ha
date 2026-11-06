# Awenta HRV Home Assistant Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MrHorvatHD&repository=awenta_ha&category=Integration)
[![GitHub Release](https://img.shields.io/github/v/release/MrHorvatHD/awenta_ha?label=release&style=flat-square)](https://github.com/MrHorvatHD/awenta_ha/releases)
[![License](https://img.shields.io/github/license/MrHorvatHD/awenta_ha?style=flat-square)](https://github.com/MrHorvatHD/awenta_ha/blob/master/LICENSE)

---

> Maintained fork of [MateiiK/awenta_ha](https://github.com/MateiiK/awenta_ha) (original by MateiK, MIT) — the upstream
> project is inactive. **2.0 adds fully local control: Home Assistant itself is the server the units connect to, no Awenta
> cloud or account needed.** The cloud mode of 1.x is still there as a fallback.

## Overview

This integration adds support for **Awenta HRV (Heat Recovery Ventilation) units** to Home Assistant:

- Power on/off and fan speed (gear 1–3) · work mode (Recuperation / Supply / Extract)
- Temperature, humidity and filter hours left sensors
- Display button (one press of the unit's DISP button) and a filter reset button
- **Local mode (new in 2.0, recommended):** the units connect to Home Assistant instead of Awenta's cloud. Works without
  internet, without the Awenta app and without an account; commands take effect immediately.
- **Cloud mode:** control through Awenta's cloud with your Awenta account (as in 1.x).

## Installation

### HACS (recommended)
1. HACS → Integrations → ⋮ → Custom repositories → `https://github.com/MrHorvatHD/awenta_ha`, category **Integration**
2. Download and restart Home Assistant
3. **Settings → Devices & services → Add integration → Awenta HRV** and choose **Local** or **Cloud**

### Manual
Copy `custom_components/awenta_ahr` to `/config/custom_components/awenta_ahr`, restart, add the integration.

## Local mode

The units are websocket *clients*: they connect to `wss://ahr.awenta.pl:31990/`. They look the name up in DNS and do **not**
validate the server certificate, so all it takes is to make that name point at your Home Assistant:

1. Give Home Assistant a **fixed IP** (DHCP reservation in your router).
2. Add a **local DNS record** `ahr.awenta.pl` → *the Home Assistant IP* (UniFi: Settings → Routing/Policy table → DNS; AdGuard,
   Pi-hole, dnsmasq… work the same). Nothing else on your network needs the real name.
3. Add the integration in **local** mode (default port 31990; Home Assistant's own process listens, the port must be reachable
   from the units — on Home Assistant OS it is).
4. **Power-cycle each unit once** (or wait for it to reconnect). A unit shows up when it connects: its entities appear and are
   named *Awenta XXXX* (the last bytes of its MAC); rename them under **Configure** (Settings → Devices & services → Awenta HRV →
   Configure) — the names are used for entities created afterwards, existing entities can be renamed in the usual way.

When Home Assistant is not running the units keep working with their own settings; they reconnect when it is back (give them a
minute). The entities of a unit that is not connected show as *unavailable*.

**Switching an existing cloud setup to local:** open **Configure** on the existing entry, choose mode *local*, do steps 1–2 and
power-cycle the units. Entity ids and unique ids stay the same, so dashboards and automations keep working. The unit names are
remembered from the cloud while the entry still runs in cloud mode (upgrade first, let it start once, then switch). To go back,
choose *cloud* again and delete the DNS record.

**What local mode cannot do:** the official Awenta app stops working while the DNS record is in place (it talks to the cloud
about units that are connected to Home Assistant instead); firmware updates from Awenta and the master/slave *synchro* command
are not available. The protocol also allows hygrostat, timer and night-mode settings — they are decoded (see
[docs/protocol.md](docs/protocol.md)) but not exposed as entities yet.

## Cloud mode

Choose *Cloud* and enter your Awenta account. Home Assistant talks to `ahr.awenta.pl` as the app does; this needs internet and
Awenta's cloud. It is the fallback if local mode does not fit.

## Entities (per unit)

| Entity | Description |
|---|---|
| `fan.<unit>` | power, fan speed Low / Medium / High (gear 1–3). In hygrostat mode the unit overrides the gear (3 when humid, 0 = idle when dry) |
| `select.<unit>_mode` | Recuperation / Supply / Extract |
| `sensor.<unit>_temperature`, `sensor.<unit>_humidity` | room sensor |
| `sensor.<unit>_filter_hours_left` | hours until the filter must be replaced (2160 after a reset) |
| `button.<unit>_display` | one DISP press: dimmed → humidity → temperature → clock → automatic → dimmed … The unit does not report which screen it shows, so to reach a given screen from an automation keep track of the position yourself (e.g. an `input_select`) |
| `button.<unit>_filter_reset` | filter hours back to 2160 after a filter change. Only works **while the unit is running** (the unit ignores it otherwise, the official app hides the option) — pressing it while the unit is off fails with an explanation |

## Upgrading from 1.x

Existing entries keep working in **cloud** mode, nothing changes until you pick *local* under **Configure**. 2.0 stores the unit
names in the entry so they survive the switch.

## Protocol

See [docs/protocol.md](docs/protocol.md): frame scrambling, the state report and every command, found by decompiling the official
app and capturing the units' traffic. For the cloud mode the unit commands are sent as JSON over the cloud websocket:

### Cloud JSON commands (official app 1.1.9)

`wss://ahr.awenta.pl:31990/`, JSON messages, each with `id`, `key` (from the login) and the unit's `mac`:

| `act` | Extra fields | Meaning |
|---|---|---|
| `join` | — | subscribe to a unit's live data |
| `send_power_on` / `send_power_off` | — | power |
| `send_gear_number` | `gear_nr` 1–3 | fan speed |
| `send_work_mode` | `mode_nr` 0 extract, 1 supply, 2 recuperation | work mode |
| `send_higro_level` | `level` 0–9 | humidity threshold (0 = off) |
| `send_timer_level` | `level` 0–8 | timer |
| `set_night_on` / `set_night_off`, `set_time_night_on` / `set_time_night_off` | time fields | night mode |
| `set_display` | — | one DISP press |
| `set_filter_reset` | — | filter counter back to 2160 h; the unit ignores it while switched off (the app hides the option then) |
| `set_synchro_on` / `set_synchro_off` | — | master/slave sync |


## Development

The protocol and the local server are plain Python (no Home Assistant needed): `python3 -m unittest discover -s tests`
(needs `openssl` for a throw-away certificate). The tests run a fake unit against the server.

---

## Support / Donate

If you like this integration, you can support development:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/MateiK)

---

## License

MIT License — see [LICENSE](https://github.com/MrHorvatHD/awenta_ha/blob/master/LICENSE)

