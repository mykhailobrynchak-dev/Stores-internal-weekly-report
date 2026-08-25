"""Sanity-check data.json before it is published.

Runs after build_report.py in CI so an upstream schema or scope change fails the
job instead of silently pushing an empty or truncated report.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).with_name("data.json")
DATASETS = (
    "weekly_partner",
    "weekly_economics",
    "weekly_campaigns",
    "weekly_refund_reasons",
    "weekly_mtd_partner",
)


def main() -> int:
    payload = json.loads(DATA.read_text())
    problems: list[str] = []

    for name in DATASETS:
        if not payload.get(name):
            problems.append(f"{name} is empty")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    weeks = sorted({row["week_start"] for row in payload["weekly_partner"]})
    today = date.today()
    expected_latest = today - timedelta(days=today.weekday() + 7)

    if weeks[-1] != expected_latest.isoformat():
        problems.append(f"latest week is {weeks[-1]}, expected {expected_latest.isoformat()}")

    first, last = date.fromisoformat(weeks[0]), date.fromisoformat(weeks[-1])
    span = [
        (first + timedelta(days=7 * offset)).isoformat()
        for offset in range((last - first).days // 7 + 1)
    ]
    gaps = sorted(set(span) - set(weeks))
    if gaps:
        problems.append(f"missing weeks: {', '.join(gaps)}")

    latest = [row for row in payload["weekly_partner"] if row["week_start"] == weeks[-1]]
    orders = sum(row["orders"] for row in latest)
    gmv = sum(row["gmv_eur"] for row in latest)
    if orders <= 0:
        problems.append(f"latest week has {orders} orders")
    if gmv <= 0:
        problems.append(f"latest week has {gmv} GMV")
    if not any(row["week_start"] == weeks[-1] for row in payload["weekly_campaigns"]):
        problems.append(f"no campaigns recorded for {weeks[-1]}")

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1

    print(
        f"OK: {len(weeks)} contiguous weeks through {weeks[-1]}; "
        f"latest orders={orders:,}, GMV={gmv:,.0f}, partners={len(latest)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
