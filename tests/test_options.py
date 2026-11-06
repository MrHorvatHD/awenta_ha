"""Hygrostat / timer option tables and their commands (stdlib only)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from _load import load  # noqa: E402

const = load("const")
frames = load("frames")


class OptionTablesTest(unittest.TestCase):
    def test_hygrostat_levels_map_to_thresholds(self):
        self.assertEqual(const.HYGROSTAT_OPTIONS[0], "Off")
        self.assertEqual(const.HYGROSTAT_OPTIONS[1], "10 %")
        self.assertEqual(const.HYGROSTAT_OPTIONS[9], "90 %")
        self.assertEqual(len(const.HYGROSTAT_OPTIONS), 10)

    def test_timer_levels_map_to_minutes(self):
        self.assertEqual(const.TIMER_OPTIONS, ["Off", "5 min", "10 min", "15 min", "30 min", "45 min", "60 min",
                                               "120 min", "180 min"])

    def test_every_option_has_a_valid_command(self):
        for level, _ in enumerate(const.HYGROSTAT_OPTIONS):
            self.assertEqual(frames.command_payloads({"act": "send_higro_level", "level": level}), [bytes([8, level])])
        for level, _ in enumerate(const.TIMER_OPTIONS):
            self.assertEqual(frames.command_payloads({"act": "send_timer_level", "level": level}), [bytes([9, level])])

    def test_option_ids_match_the_unit_report(self):
        self.assertEqual((const.OPTION_TIMER, const.OPTION_HYGROSTAT), (1, 2))


if __name__ == "__main__":
    unittest.main()
