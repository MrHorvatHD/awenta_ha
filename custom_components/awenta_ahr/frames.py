"""Awenta AHR unit protocol: scrambled binary frames inside the unit's websocket.

Pure Python, no Home Assistant imports.

Frame = payload + XOR checksum of the payload, every byte XORed with TABLE[(index + rnd) & 255], rnd (a random
byte) appended. Server -> unit commands use ENC, unit -> server reports use DEC (same as the BLE/TCP pairing
protocol of the official app).
The protocol was reverse-engineered from the official app and captured traffic; see docs/protocol.md.
"""
import os

DEFAULT_TIMEZONE = "CET-1CEST,M3.5.0,M10.5.0/3"

ENC = (
    91, 208, 27, 232, 33, 118, 131, 59, 149, 95, 83, 19, 192, 176, 25, 243,
    74, 96, 237, 8, 32, 67, 123, 120, 20, 109, 117, 130, 89, 188, 193, 23,
    119, 238, 124, 125, 207, 16, 233, 241, 10, 145, 132, 100, 75, 254, 224, 18,
    178, 171, 110, 69, 206, 162, 194, 28, 86, 167, 214, 183, 2, 5, 227, 218,
    160, 58, 161, 211, 55, 164, 41, 56, 116, 252, 253, 147, 197, 22, 45, 24,
    138, 94, 203, 174, 76, 121, 72, 213, 47, 93, 35, 43, 64, 52, 236, 4,
    172, 165, 198, 14, 99, 15, 221, 12, 140, 61, 212, 210, 163, 50, 90, 77,
    134, 191, 53, 169, 65, 60, 151, 44, 246, 215, 170, 225, 139, 255, 248, 73,
    17, 247, 231, 38, 88, 31, 184, 127, 141, 190, 48, 26, 168, 128, 57, 251,
    6, 219, 175, 135, 1, 84, 202, 115, 29, 155, 39, 150, 111, 249, 143, 142,
    71, 152, 196, 179, 80, 63, 240, 104, 7, 187, 40, 129, 11, 133, 144, 126,
    173, 181, 222, 182, 92, 114, 78, 205, 51, 113, 21, 199, 250, 54, 13, 153,
    79, 180, 226, 36, 195, 148, 201, 223, 234, 87, 112, 85, 49, 101, 107, 159,
    34, 177, 242, 209, 46, 228, 68, 204, 98, 245, 136, 216, 42, 81, 106, 229,
    166, 156, 70, 105, 158, 108, 200, 9, 235, 0, 189, 3, 30, 244, 157, 220,
    37, 137, 154, 102, 82, 103, 122, 146, 185, 62, 230, 217, 66, 239, 186, 97,
)
DEC = (
    5, 126, 160, 136, 156, 162, 240, 179, 32, 146, 222, 33, 131, 188, 102, 223,
    29, 253, 76, 72, 168, 206, 10, 235, 209, 243, 94, 49, 215, 249, 118, 204,
    170, 167, 35, 241, 181, 173, 11, 251, 51, 244, 125, 130, 225, 254, 23, 176,
    54, 229, 0, 109, 203, 3, 183, 56, 107, 172, 175, 158, 62, 186, 213, 39,
    24, 15, 108, 212, 142, 111, 41, 100, 238, 78, 21, 169, 71, 121, 8, 207,
    214, 161, 250, 233, 246, 7, 252, 153, 231, 227, 116, 4, 247, 89, 178, 104,
    30, 86, 101, 200, 128, 61, 34, 184, 187, 135, 119, 117, 226, 14, 228, 234,
    152, 211, 193, 133, 180, 220, 45, 20, 18, 190, 219, 148, 237, 38, 95, 127,
    132, 141, 129, 218, 17, 50, 68, 139, 115, 58, 46, 87, 112, 103, 171, 216,
    255, 122, 75, 27, 134, 42, 163, 52, 48, 82, 191, 177, 74, 96, 194, 145,
    31, 232, 224, 67, 93, 2, 205, 99, 140, 53, 9, 114, 174, 192, 123, 137,
    16, 6, 155, 85, 196, 77, 248, 90, 230, 81, 164, 154, 84, 110, 63, 26,
    92, 124, 60, 144, 138, 91, 88, 242, 159, 202, 105, 69, 28, 40, 97, 79,
    198, 44, 182, 64, 197, 73, 208, 195, 236, 106, 65, 13, 57, 37, 19, 12,
    221, 239, 25, 55, 147, 245, 1, 151, 150, 165, 185, 210, 189, 120, 66, 157,
    217, 59, 199, 43, 166, 201, 70, 22, 113, 83, 98, 36, 47, 143, 149, 80,
)


def _xor_frame(payload, table, rnd):
    chk = 0
    for b in payload:
        chk ^= b
    body = bytes(payload) + bytes([chk])
    return bytes(b ^ table[(i + rnd) & 255] for i, b in enumerate(body)) + bytes([rnd])


def _unxor_frame(frame, table):
    if len(frame) < 3:
        raise ValueError("frame too short")
    rnd = frame[-1]
    body = bytes(b ^ table[(i + rnd) & 255] for i, b in enumerate(frame[:-1]))
    chk = 0
    for b in body:
        chk ^= b
    if chk:
        raise ValueError("bad checksum")
    return body[:-1]


def encode_command(payload, rnd=None):
    """Frame a server -> unit command."""
    return _xor_frame(payload, ENC, os.urandom(1)[0] if rnd is None else rnd)


def decode_command(frame):
    """Inverse of encode_command (tests / fake servers)."""
    return _unxor_frame(frame, ENC)


def encode_report(payload, rnd=None):
    """Frame a unit -> server report (tests / fake units)."""
    return _xor_frame(payload, DEC, os.urandom(1)[0] if rnd is None else rnd)


def decode_report(frame):
    """Payload of a unit -> server report; raises ValueError on a bad checksum."""
    return _unxor_frame(frame, DEC)


def mac_of(payload):
    return ":".join("%02X" % b for b in payload[:6])


def parse_state(payload):
    """State report (type 0x01, 71 bytes) -> the dict the cloud's JSON status used, so entities work in both modes."""
    if len(payload) < 71 or payload[6] != 1:
        return None

    def be(i):
        return (payload[i] << 8) | payload[i + 1]

    return {
        "data_valid": True,
        "power": bool(payload[13]),
        "recuperation_gear_adv": payload[14],
        "temperature_sensor": be(26),
        "humidity_sensor": be(28),
        "valid_sensor": True,
        "mode": payload[56],
        "option": payload[57],
        "ht_level": payload[59],
        "timer_level": payload[60],
        "timer_left": payload[61],
        "time_rtc": be(62),
        "time_night_on": be(64),
        "time_night_off": be(66),
        "time_filter_time_left": be(68),
        "used_sensor": payload[70],
    }


def parse_timezone(payload):
    """Type 0x03 message the unit sends after connecting: POSIX timezone string it is configured with."""
    if len(payload) < 10 or payload[6] != 3:
        return None
    return payload[9:].split(b"\0")[0].decode("ascii", "replace")


def _minutes(h, m):
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("time out of range")
    return (h * 60 + m).to_bytes(2, "big")


def _level(value, high):
    value = int(value)
    if not 0 <= value <= high:
        raise ValueError("level out of range")
    return value


def command_payloads(command, timezone=None):
    """Cloud-style command dict ({"act": ..., ...}) -> list of unit payloads (before scrambling).

    Raises ValueError for commands the unit cannot take locally (synchro, firmware update) or bad parameters.
    """
    act = command.get("act")
    tz = (timezone or DEFAULT_TIMEZONE).encode("ascii") + b"\0"
    if act == "send_power_on":
        return [b"\x05\x01"]
    if act == "send_power_off":
        return [b"\x05\x00"]
    if act == "send_gear_number":
        gear = int(command["gear_nr"])
        if not 1 <= gear <= 3:
            raise ValueError("gear out of range")
        return [bytes([6, gear])]
    if act == "send_work_mode":
        return [bytes([7, _level(command["mode_nr"], 2)])]
    if act == "send_higro_level":
        return [bytes([8, _level(command["level"], 9)])]
    if act == "send_timer_level":
        return [bytes([9, _level(command["level"], 8)])]
    if act == "set_night_on":
        return [b"\x0a\x01"]
    if act == "set_night_off":
        return [b"\x0a\x00"]
    if act == "set_time_night_on":
        return [b"\x0f" + _minutes(command["h"], command["m"])]
    if act == "set_time_night_off":
        return [b"\x10" + _minutes(command["h"], command["m"])]
    if act == "set_time_auto":
        return [b"\x04\x01\x00" + tz]
    if act == "set_time_manual":
        return [b"\x04\x00\x00" + tz, b"\x0e" + _minutes(command["h"], command["m"])]
    if act == "set_display":
        return [b"\x0b\x00"]
    if act == "set_filter_reset":
        return [b"\x0d\x01"]
    raise ValueError(f"command {act!r} is not supported in local mode")


def ws_frame(opcode, payload=b""):
    """Server -> client websocket frame (unmasked, FIN set)."""
    n = len(payload)
    if n < 126:
        head = bytes([0x80 | opcode, n])
    elif n < 65536:
        head = bytes([0x80 | opcode, 126]) + n.to_bytes(2, "big")
    else:
        head = bytes([0x80 | opcode, 127]) + n.to_bytes(8, "big")
    return head + payload
