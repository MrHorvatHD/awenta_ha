# Awenta AHR unit protocol (as used by the local mode)

Reverse-engineered from the official app (`com.awenta.pro` 2025_10_04) and from captured traffic of two AHR units. Not an official
specification; verified on two units (firmware 2.3). The same format carries the pairing frames of the app (BLE / TCP 14014).

## Connection
- The unit is a websocket **client**: TLS (1.2, `ECDHE-RSA-AES256-GCM-SHA384`) to `ahr.awenta.pl:31990`, `GET /` with
  `Upgrade: websocket`, `User-Agent: ESP32 Websocket Client`. The name is resolved through DNS, the server certificate is **not
  validated**, there is no authentication.
- After the upgrade the unit sends binary frames (reports) about every 5 s and whenever something changes, and pings; the cloud pings the
  unit about every 10 s. A unit that is not answered / pinged reconnects.
- The cloud sends nothing else unprompted: no time sync, no configuration (the unit has its own NTP).

## Frame scrambling
`payload | XOR checksum of the payload`, every byte XORed with `TABLE[(index + rnd) & 255]`, then `rnd` (a random byte) appended.
Server → unit frames use the `ENC` table, unit → server frames use `DEC` (see `custom_components/awenta_ahr/frames.py`).

## Unit → server
Payload: bytes 0–5 MAC, byte 6 message type.

| Type | Meaning |
|---|---|
| `0x01` (71 bytes) | state report |
| `0x03` | after connecting: `03 <auto> 00 <POSIX timezone>\0`, e.g. `CET-1CEST,M3.5.0,M10.5.0/3` |

State report (16-bit values big-endian):

| idx | Field | Cloud JSON name |
|---|---|---|
| 13, 54 | power (0/1) | `power` |
| 14, 55 | gear actually running (0 when off or idle in hygrostat mode, 1–3) | `recuperation_gear_adv` |
| 12 | 1 for ~1 s while the damper moves | |
| 26–27 | temperature × 10 | `temperature_sensor` |
| 28–29 | humidity × 10 | `humidity_sensor` |
| 56 | work mode 0 extract / 1 supply / 2 recuperation | `mode` |
| 57 | active extra option: 0 manual, 1 timer, 2 hygrostat (3 = night, inferred) | `option` |
| 59 | hygrostat level 0–9 | `ht_level` |
| 60 / 61 | timer level 0–8 / minutes left | `timer_level` / `timer_left` |
| 62–63 | unit clock, minutes since midnight | `time_rtc` |
| 64–65 / 66–67 | night start / end, minutes since midnight | `time_night_on` / `time_night_off` |
| 68–69 | filter hours left (2160 after a reset) | `time_filter_time_left` |
| 70 | used sensor | `used_sensor` |

Unmapped: idx 16–25 (raw sensor values), synchro flags, sensor-valid flags, firmware versions.

## Server → unit commands
| Cloud `act` | Payload | Notes |
|---|---|---|
| `send_power_on` / `send_power_off` | `05 01` / `05 00` | switching on resumes the last gear |
| `send_gear_number` 1–3 | `06 01..03` | |
| `send_work_mode` 0/1/2 | `07 00..02` | |
| `send_higro_level` 0–9 | `08 LL` | only effective while the unit is on; level 0 = off |
| `send_timer_level` 0–8 | `09 LL` | off, 5, 10, 15, 30, 45, 60, 120, 180 min; only while on; **the unit switches itself off when it expires** |
| `set_night_on` / `set_night_off` | `0a 01` / `0a 00` | |
| `set_time_night_on` h,m / `set_time_night_off` h,m | `0f HH HH` / `10 HH HH` | minutes since midnight |
| `set_time_auto` | `04 01 00 <timezone>\0` | |
| `set_time_manual` h,m | `04 00 00 <timezone>\0`, then `0e HH HH` | |
| `set_display` | `0b 00` | one DISP press |
| `set_filter_reset` | `0d 01` | filter hours back to 2160; **ignored while the unit is off** |
| `set_synchro_on/off`, `set_update` | — | not supported in local mode |

Hygrostat mode: the unit overrides the gear — gear 3 while the room humidity is above the threshold, gear 0 (powered on, idle) below it.
Only one extra option (manual / timer / hygrostat) is active at a time.
