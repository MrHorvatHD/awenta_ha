# Awenta HRV Home Assistant Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MrHorvatHD&repository=awenta_ha&category=Integration)
[![GitHub Release](https://img.shields.io/github/v/release/MrHorvatHD/awenta_ha?label=release&style=flat-square)](https://github.com/MrHorvatHD/awenta_ha/releases)
[![License](https://img.shields.io/github/license/MrHorvatHD/awenta_ha?style=flat-square)](https://github.com/MrHorvatHD/awenta_ha/blob/master/LICENSE)

---

> Maintained fork of [MateiiK/awenta_ha](https://github.com/MateiiK/awenta_ha) (original by MateiK, MIT) — the upstream
> project is inactive. Fixes: config flow domain, HACS install, retry/cleanup, non-blocking SSL, real power on/off,
> display button.

## Overview

This integration adds support for **Awenta HRV (Heat Recovery Ventilation) units** to Home Assistant, including:

- Power on/off and fan speed control (Low / Medium / High)
- Display button: one press of the unit's DISP button (see below)
- Temperature, Humidity, and Filter sensors
- Mode selection (Recuperation / Supply / Extract)
- Automatic updates via HACS

---

## Installation

### HACS (Recommended)

1. Open Home Assistant → HACS → Integrations → ⋮ → Custom Repositories  
2. Repository URL: `https://github.com/MrHorvatHD/awenta_ha`  
3. Category: **Integration**  
4. Install and restart Home Assistant  
5. Add the integration via **Settings → Devices & Services → Add Integration → Awenta HRV**

### Manual Install

1. Download the repository ZIP: [Download ZIP](https://github.com/MrHorvatHD/awenta_ha/archive/refs/heads/master.zip)  
2. Extract and copy the folder to:
/config/custom_components/awenta_ahr
3. Restart Home Assistant  
4. Add the integration via **Settings → Devices & Services → Add Integration → Awenta HRV**

---

## Usage

- The fan slider represents **Low, Medium, High** speeds.  
- Sensors update automatically via WebSocket.  
- Modes and other options are available in the **Fan and Select entities**.
- **Display button** (`button.<unit>_display`): each press moves the unit's display one step, exactly like DISP on the
  unit: dimmed → humidity → temperature → clock → automatic → dimmed … The unit does not report which screen it shows,
  so to reach a given screen from an automation, keep track of the position yourself (e.g. an `input_select`) and press
  the button the right number of times.

## Cloud protocol (from the official Awenta AHR app 1.1.9)

WebSocket `wss://ahr.awenta.pl:31990/`, JSON messages, each with `id`, `key` (from the login) and the unit's `mac`:

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
| `set_filter_reset` | — | reset the filter counter |
| `set_synchro_on` / `set_synchro_off` | — | master/slave sync |

---

## Support / Donate

If you like this integration, you can support development:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/MateiK)

---

## License

MIT License — see [LICENSE](https://github.com/MrHorvatHD/awenta_ha/blob/master/LICENSE)

