# Awenta HRV Home Assistant Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MateiiK&repository=awenta_ha&category=Integration)
[![GitHub Release](https://img.shields.io/github/v/release/MateiiK/awenta_ha?label=release&style=flat-square)](https://github.com/MateiiK/awenta_ha/releases)
[![License](https://img.shields.io/github/license/MateiiK/awenta_ha?style=flat-square)](https://github.com/MateiiK/awenta_ha/blob/main/LICENSE)

---

## Overview

This integration adds support for **Awenta HRV (Heat Recovery Ventilation) units** to Home Assistant, including:

- Fan speed control (Low / Medium / High)
- Temperature, Humidity, and Filter sensors
- Mode selection (Recuperation / Supply / Extract)
- Automatic updates via HACS

---

## Installation

### HACS (Recommended)

1. Open Home Assistant → HACS → Integrations → ⋮ → Custom Repositories  
2. Repository URL: `https://github.com/MateiiK/awenta_ha`  
3. Category: **Integration**  
4. Install and restart Home Assistant  
5. Add the integration via **Settings → Devices & Services → Add Integration → Awenta HRV**

### Manual Install

1. Download the repository ZIP: [Download ZIP](https://github.com/MateiiK/awenta_ha/archive/refs/heads/main.zip)  
2. Extract and copy the folder to:
/config/custom_components/awenta_ahr
3. Restart Home Assistant  
4. Add the integration via **Settings → Devices & Services → Add Integration → Awenta HRV**

---

## Usage

- The fan slider represents **Low, Medium, High** speeds.  
- Sensors update automatically via WebSocket.  
- Modes and other options are available in the **Fan and Select entities**.

---

## Support / Donate

If you like this integration, you can support development:

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/MateiK)

---

## License

MIT License — see [LICENSE](https://github.com/MateiiK/awenta_ha/blob/main/LICENSE)

