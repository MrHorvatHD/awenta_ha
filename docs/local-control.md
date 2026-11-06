# Local control

Since 2.0 the integration can control the units **without Awenta's cloud**: Home Assistant itself is the server the units
connect to. This page explains how it works and what you have to do to switch it on.

## How it works

By default an Awenta AHR unit opens a TLS connection to `ahr.awenta.pl:31990`, upgrades it to a websocket and keeps it open.
The state of the unit goes up that connection (about every 5 seconds), and commands from the Awenta app come down it. The unit
does not listen on any port, so there is nothing to connect to locally — but the unit looks the server name up in DNS and
does **not** check the server's certificate.

Local mode uses exactly that:

```
                     cloud mode (1.x)                       local mode (2.0)

  unit ──TLS/websocket──► ahr.awenta.pl ◄── Home Assistant     unit ──TLS/websocket──► Home Assistant
        (Awenta's server)                    (as the app does)        (ahr.awenta.pl → your HA by local DNS)
```

1. You add a **local DNS record** `ahr.awenta.pl` → the IP of your Home Assistant.
2. The integration starts a small TLS/websocket server on port **31990** inside Home Assistant (a self-signed certificate for
   `ahr.awenta.pl` is created on first start in `/config/.storage/`).
3. A unit that (re)connects now finds Home Assistant instead of Awenta's server. It sends its state reports; the integration
   turns them into the usual entities and sends commands back over the same connection.

Nothing leaves your network, no account is needed, and a command is on the unit within a fraction of a second. The wire format
(scrambled binary frames) is documented in [protocol.md](protocol.md).

## What you need

- Home Assistant with the integration installed (HACS, see the README), **Home Assistant OS / Supervised or any installation where
  Home Assistant is reachable on its own IP and may open port 31990** (the units must reach it).
- A **fixed IP** for Home Assistant (DHCP reservation in your router).
- A router/DNS server that can serve a **local DNS record**. All of these work: UniFi, AdGuard Home, Pi-hole, dnsmasq/OpenWrt,
  Mikrotik, pfSense/OPNsense, a Fritz!Box (host name override).
- The units on the same network (or a network that may reach Home Assistant on port 31990).

## Enable it

1. **Fixed IP.** Reserve an IP for Home Assistant in your router (below: `192.168.1.10`).
2. **DNS record.** Create an *A record* for `ahr.awenta.pl` pointing to that IP, on the DNS server your units use:
   - **UniFi:** Settings → Routing → DNS (or *Policy Table → DNS*) → create a record `ahr.awenta.pl` → `192.168.1.10`
   - **AdGuard Home:** Filters → DNS rewrites → add `ahr.awenta.pl` → `192.168.1.10`
   - **Pi-hole:** Settings → Local DNS records → `ahr.awenta.pl` → `192.168.1.10`
   - **dnsmasq / OpenWrt:** `address=/ahr.awenta.pl/192.168.1.10`
   - Check from a computer on the same network: `nslookup ahr.awenta.pl` must answer the Home Assistant IP.
3. **Switch the integration to local mode.**
   - *New setup:* Settings → Devices & services → Add integration → **Awenta HRV** → **Local**.
   - *Existing 1.x setup:* open the integration → **Configure** → mode **local**. Do this while the entry still runs in cloud
     mode once after the upgrade, so it can remember the unit names (see below).
4. **Power-cycle each unit** (switch it off and on at the unit; the units re-resolve the name when they reconnect). Within about
   a minute the unit appears: its entities become available.
5. **Check:** the entities show live values; change the fan speed from Home Assistant and watch the unit follow.

Units that Home Assistant has not seen before are created automatically and named *Awenta XXXX* (the last bytes of the MAC).
Rename them under **Configure** (one field per unit; the names apply to entities created afterwards, existing entities can also
be renamed in the usual way). Entity ids and unique ids are built from the MAC, so switching an existing setup from cloud to
local keeps your entities, dashboards and automations.

## If Home Assistant is down

The units keep running with their own settings, but nobody can control them. When Home Assistant is back they normally
reconnect on their own within about a minute (in tests: ~18 seconds after the integration was reloaded). **If a unit does not
come back, power-cycle it** — switch it off and on at the unit — so that it reconnects. The same applies after a longer outage of
Home Assistant, after changing the DNS record, or after changing the port.

While a unit is not connected its entities are shown as *unavailable* (not with stale values).

## Troubleshooting

| Symptom | Check |
|---|---|
| Entities stay *unavailable* after the power cycle | `nslookup ahr.awenta.pl` from the network of the units must return the Home Assistant IP; some routers cache DNS answers for minutes — wait or restart the DNS service |
| | Port 31990 must be reachable on Home Assistant (`nc -vz <ha-ip> 31990` from another machine); check firewalls and VLAN rules between the units and Home Assistant |
| | Settings → System → Logs: *Awenta unit server could not start on port …* means the port is already in use; pick another port under **Configure** (and set it in the router: the units always use 31990, so another port only works behind a port redirect) |
| Home Assistant itself cannot reach Awenta's cloud any more | Expected: with the DNS record in place the cloud mode (and the Awenta app) cannot work. Switch the entry to cloud mode **and** delete the record to go back |
| Units show up as *Awenta XXXX* | They are new to Home Assistant; rename them under **Configure** |
| A unit disconnects every few minutes | Wi-Fi/range problem of the unit; check the unit's signal. The unit server drops a connection that has been silent for 60 seconds |

## Security notes

- The server listens on all interfaces of Home Assistant on port 31990 and **does not authenticate** units — anyone on the network
  who knows the format could send reports or connect. Keep the units (and this port) on a trusted network or VLAN; do not expose
  the port to the internet.
- The units do not validate certificates; that is a property of the units, not of this integration.
- The DNS record only redirects the name `ahr.awenta.pl`; other devices keep using the real Awenta cloud for anything else.

## Switching back to the cloud

Open **Configure**, choose **cloud** (this needs an entry created with an Awenta account), delete the DNS record and power-cycle
the units. The cloud mode and the DNS record exclude each other.

## Not available in local mode

- The official Awenta app (it talks to the cloud, which no longer sees the units).
- Firmware updates from Awenta and the master/slave *synchro* command (`set_synchro_*`, `set_update`).
- Night mode (on/off, start/end time) works on the protocol level (see protocol.md) but is not exposed as entities yet. Hygrostat and timer are available as selects since 2.1.
