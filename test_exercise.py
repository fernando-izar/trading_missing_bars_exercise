import unittest
from datetime import datetime, timedelta

from exercise import Bar, Quote, BarSeriesFiller, _d, _round_decimal


def _build_bar(start_iso: str, o: float, c: float, h: float, l: float) -> Bar:
    start = datetime.fromisoformat(start_iso)
    end = start + timedelta(minutes=5)
    return Bar(start=start, end=end, open=_d(o), close=_d(c), high=_d(h), low=_d(l))


class TestFiller(unittest.TestCase):
    def setUp(self):
        self.filler = BarSeriesFiller()

    def test_single_missing_bar(self):
        quote = Quote(
            open=_d(1), high=_d(1), low=_d(1), last=_d(1), previous_close=_d(100)
        )
        bars = [
            _build_bar("2025-02-19T09:30:00-05:00", 100, 101, 101, 100),
            _build_bar(
                "2025-02-19T09:40:00-05:00", 101, 102, 102, 101
            ),  # missing 09:35
        ]
        filled = self.filler.fill(bars, quote)
        self.assertEqual(filled[0].start.isoformat(), "2025-02-19T09:30:00-05:00")
        self.assertEqual(filled[1].start.isoformat(), "2025-02-19T09:35:00-05:00")
        self.assertEqual(filled[1].open, _d(101))
        self.assertEqual(filled[1].close, _d(101))

    def test_multiple_consecutive_missing_bars(self):
        quote = Quote(
            open=_d(1), high=_d(1), low=_d(1), last=_d(1), previous_close=_d(200)
        )
        bars = [
            _build_bar("2025-02-19T09:30:00-05:00", 200, 205, 206, 199),
            _build_bar(
                "2025-02-19T09:50:00-05:00", 205, 210, 211, 204
            ),  # missing 09:35, 09:40, 09:45
        ]
        filled = self.filler.fill(bars, quote)
        self.assertEqual(filled[1].start.isoformat(), "2025-02-19T09:35:00-05:00")
        self.assertEqual(filled[1].close, _d(205))
        self.assertEqual(filled[2].start.isoformat(), "2025-02-19T09:40:00-05:00")
        self.assertEqual(filled[2].close, _d(205))
        self.assertEqual(filled[3].start.isoformat(), "2025-02-19T09:45:00-05:00")
        self.assertEqual(filled[3].close, _d(205))

    def test_first_interval_missing_uses_previous_close(self):
        quote = Quote(
            open=_d(1), high=_d(1), low=_d(1), last=_d(1), previous_close=_d(300)
        )
        bars = [
            _build_bar(
                "2025-02-19T09:35:00-05:00", 301, 302, 303, 300
            ),  # missing 09:30
        ]
        filled = self.filler.fill(bars, quote)
        self.assertEqual(filled[0].start.isoformat(), "2025-02-19T09:30:00-05:00")
        self.assertEqual(filled[0].open, _d(300))
        self.assertEqual(filled[0].close, _d(300))

    def test_change_calculation(self):
        bar = _build_bar("2025-02-19T09:30:00-05:00", 100, 110, 110, 99)
        b = bar.with_calculated_change()
        self.assertEqual(b.change, _d(10))
        self.assertEqual(_round_decimal(b.percent_change, 2), _d("10.00"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
