# Exercise 1 – Filling in missing bars and calculate change for a chart

## Scenario

- Assume that today is 2025-02-19.
- The trading day starts at 09:30 and ends at 16:00.
- You are given the following JSON data representing stock prices over specific time intervals during a trading day and the quote for the current day:
  - https://universal.hellopublic.com/exercises/fs/quote.json
  - https://universal.hellopublic.com/exercises/fs/bars.json
- Each bar represents a 5-minute interval.
- All the values in the quote are from the current trading day except for `previousClose` which is from the previous trading day.
- There are missing bars for some intervals. For example, if there is a bar with a start time of 09:40 and the next bar has a start time of 09:50, then the bar with a start time of 09:45 is missing.


## Requirements

Your task is to identify all the missing bars and fill in the gaps to maintain a consistent time series, and calculate the change for each bar and the change for the day.

- Fetch quote and chart bars from the given URLs.
- Identify all the missing time intervals between 09:30 and 16:00 and fill in the gaps, *use data from the previous bar* to maintain continuity in the chart. If multiple bars are missing consecutively, repeat the logic for each interval.
- Calculate the change for each bar and the change for the day.
- Response should be in the following JSON format:

```json
{
  "change": 0.01,
  "percentChange": 1.0,
  "bars": [
    {
      "dateTime": "2025-02-19T09:30:00-05:00",
      "open": 407.88,
      "close": 408.695,
      "change": 0.01,
      "percentChange": 1.0
    },
    ..
  ]
}
```

### Optional requirement

Write test cases to ensure the algorithm handles all scenarios:
- Single missing bars
- Multiple consecutive missing bars
- Edge cases, such as the first interval of the day being missing
- Correct calculation of change


Feel free to add any packages you need.

## Run

```bash
$ python3 exercise.py
```
