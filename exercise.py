from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen


QUOTE_URL = "https://universal.hellopublic.com/exercises/fs/quote.json"
BARS_URL = "https://universal.hellopublic.com/exercises/fs/bars.json"


def _d(x: float | int | str) -> Decimal:
    return Decimal(str(x))


def _round_decimal(x: Decimal, places: int) -> Decimal:
    q = Decimal("1").scaleb(-places)  # 10^-places
    return x.quantize(q, rounding=ROUND_HALF_UP)


def _iso(dt: datetime) -> str:
    # Keep offset (e.g. -05:00) if dt is offset-aware.
    return dt.isoformat()


@dataclass(frozen=True)
class Quote:
    open: Decimal
    high: Decimal
    low: Decimal
    last: Decimal
    previous_close: Decimal

    @staticmethod
    def from_json(payload: Dict) -> "Quote":
        return Quote(
            open=_d(payload["open"]),
            high=_d(payload["high"]),
            low=_d(payload["low"]),
            last=_d(payload["last"]),
            previous_close=_d(payload["previousClose"]),
        )


@dataclass(frozen=True)
class Bar:
    start: datetime
    end: datetime
    open: Decimal
    close: Decimal
    high: Decimal
    low: Decimal

    @staticmethod
    def from_json(payload: Dict) -> "Bar":
        return Bar(
            start=datetime.fromisoformat(payload["startDateTime"]),
            end=datetime.fromisoformat(payload["endDateTime"]),
            open=_d(payload["open"]),
            close=_d(payload["close"]),
            high=_d(payload["high"]),
            low=_d(payload["low"]),
        )

    def with_calculated_change(self) -> "BarWithChange":
        change = self.close - self.open
        pct = Decimal("0") if self.open == 0 else (change / self.open) * Decimal("100")
        return BarWithChange(
            date_time=self.start,
            open=self.open,
            close=self.close,
            change=change,
            percent_change=pct,
        )


@dataclass(frozen=True)
class BarWithChange:
    date_time: datetime
    open: Decimal
    close: Decimal
    change: Decimal
    percent_change: Decimal

    def to_dict(self) -> Dict:
        # You can tune rounding here if your evaluator expects a specific precision.
        # These are reasonable defaults:
        change = _round_decimal(self.change, 6)
        pct = _round_decimal(self.percent_change, 4)

        return {
            "dateTime": _iso(self.date_time),
            "open": float(self.open),
            "close": float(self.close),
            "change": float(change),
            "percentChange": float(pct),
        }


class HttpJsonClient:
    def get_json(self, url: str) -> Dict | List:
        with urlopen(url) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)


class MarketDataService:
    def __init__(self, client: HttpJsonClient):
        self.client = client

    def fetch_quote(self) -> Quote:
        payload = self.client.get_json(QUOTE_URL)
        if not isinstance(payload, dict):
            raise ValueError("Quote payload must be an object")
        return Quote.from_json(payload)

    def fetch_bars(self) -> List[Bar]:
        payload = self.client.get_json(BARS_URL)
        if not isinstance(payload, list):
            raise ValueError("Bars payload must be a list")
        return [Bar.from_json(p) for p in payload]


class BarSeriesFiller:
    """
    Fills missing 5-minute bars between 09:30 and 16:00 using forward fill.

    Forward fill rule:
      - missing bar open/close/high/low = previous bar close
      - if first interval is missing, use quote.previous_close as the seed price
    """

    def __init__(self, interval_minutes: int = 5):
        self.interval = timedelta(minutes=interval_minutes)

    def build_session_bounds(self, trading_day: datetime) -> Tuple[datetime, datetime]:
        """
        Returns (session_start, session_end) datetime using the trading_day's tzinfo/offset.
        session_end is the *end time* (16:00), bars will be generated while start < session_end.
        """
        tz = trading_day.tzinfo
        day = trading_day.date()
        session_start = datetime.combine(day, time(9, 30), tzinfo=tz)
        session_end = datetime.combine(day, time(16, 0), tzinfo=tz)
        return session_start, session_end

    def fill(self, bars: List[Bar], quote: Quote) -> List[Bar]:
        if not bars:
            raise ValueError(
                "No bars received; cannot infer trading day timezone/offset"
            )

        # Map existing bars by start datetime (exact match)
        bar_map: Dict[datetime, Bar] = {b.start: b for b in bars}

        # Infer trading day & tz/offset from the first bar start
        trading_day = min(bar_map.keys())
        session_start, session_end = self.build_session_bounds(trading_day)

        filled: List[Bar] = []
        prev_close: Optional[Decimal] = None

        # Seed prev_close if first interval is missing (edge case)
        prev_close_seed = quote.previous_close

        current = session_start
        while current < session_end:
            existing = bar_map.get(current)

            if existing is not None:
                filled.append(existing)
                prev_close = existing.close
            else:
                if prev_close is None:
                    prev_close = prev_close_seed

                synthetic = Bar(
                    start=current,
                    end=current + self.interval,
                    open=prev_close,
                    close=prev_close,
                    high=prev_close,
                    low=prev_close,
                )
                filled.append(synthetic)
                # prev_close remains the same

            current += self.interval

        return filled


class ChangeCalculator:
    def day_change(self, quote: Quote) -> Tuple[Decimal, Decimal]:
        change = quote.last - quote.previous_close
        pct = (
            Decimal("0")
            if quote.previous_close == 0
            else (change / quote.previous_close) * Decimal("100")
        )
        return change, pct


class ExerciseRunner:
    def __init__(self, service: MarketDataService):
        self.service = service
        self.filler = BarSeriesFiller()
        self.calc = ChangeCalculator()

    def run(self) -> Dict:
        quote = self.service.fetch_quote()
        bars = self.service.fetch_bars()

        filled = self.filler.fill(bars, quote)
        bars_out = [b.with_calculated_change().to_dict() for b in filled]

        day_change, day_pct = self.calc.day_change(quote)

        # Round day change/pct similarly (tune if needed)
        day_change = _round_decimal(day_change, 6)
        day_pct = _round_decimal(day_pct, 4)

        return {
            "change": float(day_change),
            "percentChange": float(day_pct),
            "bars": bars_out,
        }


def main():
    # if len(sys.argv) > 1 and sys.argv[1].lower() == "test":
    #     run_tests()
    #     return

    client = HttpJsonClient()
    service = MarketDataService(client)
    runner = ExerciseRunner(service)

    result = runner.run()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
