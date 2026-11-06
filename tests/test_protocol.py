"""Protocol tests (stdlib only): python3 -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from _load import load  # noqa: E402

frames = load("frames")

# A real state report captured from a bedroom unit (powered on, gear 3, extract, 19.2 degC, 63.9 %).
REPORT = bytes.fromhex(
    "8c4b14ca2ab4012313010100000103010000e3de0d2e2ae5af0100c0027f0000000000000000000000000000000000000000000100000103"
    "00000100000002f1052801e0021b02"
)
TZ_REPORT = bytes.fromhex("8c4b14ca2ab4030100") + b"CET-1CEST,M3.5.0,M10.5.0/3\x00"


class FramesTest(unittest.TestCase):
    def test_roundtrip_all_random_bytes(self):
        for rnd in (0, 1, 77, 255):
            self.assertEqual(frames.decode_report(frames.encode_report(REPORT, rnd)), REPORT)
            self.assertEqual(frames.decode_command(frames.encode_command(b"\x05\x01", rnd)), b"\x05\x01")

    def test_bad_checksum(self):
        frame = bytearray(frames.encode_report(REPORT, 5))
        frame[10] ^= 0xFF
        with self.assertRaises(ValueError):
            frames.decode_report(bytes(frame))

    def test_parse_state_matches_cloud_values(self):
        s = frames.parse_state(REPORT)
        self.assertEqual(frames.mac_of(REPORT), "8C:4B:14:CA:2A:B4")
        self.assertEqual(
            {k: s[k] for k in ("power", "recuperation_gear_adv", "mode", "temperature_sensor", "humidity_sensor",
                               "time_filter_time_left", "time_night_on", "time_night_off", "option", "ht_level",
                               "timer_level", "timer_left", "used_sensor")},
            {"power": True, "recuperation_gear_adv": 3, "mode": 0, "temperature_sensor": 192, "humidity_sensor": 639,
             "time_filter_time_left": 539, "time_night_on": 1320, "time_night_off": 480, "option": 0, "ht_level": 0,
             "timer_level": 0, "timer_left": 0, "used_sensor": 2})

    def test_parse_state_rejects_other_types_and_short_frames(self):
        self.assertIsNone(frames.parse_state(TZ_REPORT))
        self.assertIsNone(frames.parse_state(REPORT[:50]))

    def test_timezone(self):
        self.assertEqual(frames.parse_timezone(TZ_REPORT), "CET-1CEST,M3.5.0,M10.5.0/3")
        self.assertIsNone(frames.parse_timezone(REPORT))

    def test_commands_match_captured_cloud_frames(self):
        cases = [
            ({"act": "send_power_on"}, [b"\x05\x01"]),
            ({"act": "send_power_off"}, [b"\x05\x00"]),
            ({"act": "send_gear_number", "gear_nr": 1}, [b"\x06\x01"]),
            ({"act": "send_gear_number", "gear_nr": 3}, [b"\x06\x03"]),
            ({"act": "send_work_mode", "mode_nr": 0}, [b"\x07\x00"]),
            ({"act": "send_work_mode", "mode_nr": 2}, [b"\x07\x02"]),
            ({"act": "send_higro_level", "level": 9}, [b"\x08\x09"]),
            ({"act": "send_timer_level", "level": 8}, [b"\x09\x08"]),
            ({"act": "set_night_on"}, [b"\x0a\x01"]),
            ({"act": "set_night_off"}, [b"\x0a\x00"]),
            ({"act": "set_time_night_on", "h": 21, "m": 30}, [b"\x0f\x05\x0a"]),
            ({"act": "set_time_night_off", "h": 7, "m": 45}, [b"\x10\x01\xd1"]),
            ({"act": "set_display"}, [b"\x0b\x00"]),
            ({"act": "set_filter_reset"}, [b"\x0d\x01"]),
            ({"act": "set_time_manual", "h": 13, "m": 10},
             [b"\x04\x00\x00CET-1CEST,M3.5.0,M10.5.0/3\x00", b"\x0e\x03\x16"]),
            ({"act": "set_time_auto"}, [b"\x04\x01\x00CET-1CEST,M3.5.0,M10.5.0/3\x00"]),
        ]
        for command, expected in cases:
            self.assertEqual(frames.command_payloads(command), expected, command)

    def test_timezone_is_taken_from_the_unit(self):
        self.assertEqual(frames.command_payloads({"act": "set_time_auto"}, "UTC0"), [b"\x04\x01\x00UTC0\x00"])

    def test_unsupported_and_invalid_commands(self):
        bad = [{"act": "set_synchro_on"}, {"act": "set_update"}, {"act": "nonsense"},
               {"act": "send_gear_number", "gear_nr": 0}, {"act": "send_gear_number", "gear_nr": 4},
               {"act": "send_work_mode", "mode_nr": 3}, {"act": "send_higro_level", "level": 10},
               {"act": "send_timer_level", "level": 9}, {"act": "set_time_night_on", "h": 24, "m": 0}]
        for command in bad:
            with self.assertRaises(ValueError, msg=command):
                frames.command_payloads(command)

    def test_ws_frame_lengths(self):
        self.assertEqual(frames.ws_frame(9), b"\x89\x00")
        self.assertEqual(frames.ws_frame(2, b"ab"), b"\x82\x02ab")
        self.assertEqual(frames.ws_frame(2, b"x" * 200)[:4], b"\x82\x7e\x00\xc8")


if __name__ == "__main__":
    unittest.main()
