#!/usr/bin/env python3
"""Live smoke test against the real Coway IoCare API.

Credentials are read from environment variables so they never end up in
shell history, code, or logs:

    read -s COWAY_PASSWORD && export COWAY_PASSWORD
    export COWAY_EMAIL="you@example.com"
    .venv/bin/python scripts/live_test.py

Or put them in an untracked env file (already gitignored) and source it:

    # .coway_env
    export COWAY_EMAIL="you@example.com"
    export COWAY_PASSWORD="..."

    source .coway_env && .venv/bin/python scripts/live_test.py

Options:
    --debug     enable pycoway debug logging (verbose, includes payloads)
    --repeat    poll twice to show warm-cache timing
"""

import argparse
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pycoway import CowayClient, CowayPurifier  # noqa: E402


def _mask(serial: str | None) -> str:
    if not serial:
        return "<none>"
    if len(serial) <= 6:
        return serial[0] + "***"
    return f"{serial[:4]}***{serial[-2:]}"


def _print_purifier(device_id: str, p: CowayPurifier) -> None:
    attr = p.device_attr
    print(f"\n=== {attr.name} ({_mask(device_id)}) ===")
    print(f"  model / code:        {attr.model} / {attr.model_code}")
    print(f"  network:             {p.network_status}")
    print(f"  power:               {p.is_on}")
    print(
        f"  modes:               auto={p.auto_mode} night={p.night_mode} "
        f"eco={p.eco_mode} rapid={p.rapid_mode}"
    )
    print(f"  fan speed:           {p.fan_speed}")
    print(f"  light (on/mode):     {p.light_on} / {p.light_mode}")
    print(f"  timer / remaining:   {p.timer} / {p.timer_remaining}")
    print(f"  PM2.5 / PM10:        {p.particulate_matter_2_5} / {p.particulate_matter_10}")
    print(
        f"  CO2 / VOC / IAQ:     {p.carbon_dioxide} / {p.volatile_organic_compounds} / "
        f"{p.air_quality_index}"
    )
    print(f"  AQ grade / lux:      {p.aq_grade} / {p.lux_sensor}")
    print(f"  MCU version:         {p.mcu_version}")
    print(
        f"  filters %:           pre={p.pre_filter_pct} max2={p.max2_pct} odor={p.odor_filter_pct}"
    )
    for f in p.filters or []:
        print(
            f"    - {f.name}: remain={f.filter_remain}% status={f.filter_remain_status} "
            f"cycle={f.replace_cycle}{f.replace_cycle_unit or ''} next={f.next_date}"
        )


async def run(debug: bool, repeat: bool) -> int:
    email = os.environ.get("COWAY_EMAIL")
    password = os.environ.get("COWAY_PASSWORD")
    if not email or not password:
        print("Set COWAY_EMAIL and COWAY_PASSWORD environment variables first.", file=sys.stderr)
        print("See the docstring at the top of this script for details.", file=sys.stderr)
        return 2

    if debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(name)s: %(message)s")
        logging.getLogger("pycoway").setLevel(logging.DEBUG)

    client = CowayClient(email, password, skip_password_change=True)
    try:
        t0 = time.perf_counter()
        await client.login()
        t1 = time.perf_counter()
        print(f"login: {t1 - t0:.2f}s  (places: {len(client.places or [])})")

        data = await client.async_get_purifiers_data()
        t2 = time.perf_counter()
        print(f"first poll: {t2 - t1:.2f}s  ({len(data.purifiers)} purifier(s))")

        for device_id, purifier in data.purifiers.items():
            _print_purifier(device_id, purifier)

        if repeat:
            t3 = time.perf_counter()
            await client.async_get_purifiers_data()
            print(f"\nsecond poll (warm caches): {time.perf_counter() - t3:.2f}s")
    finally:
        await client.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug", action="store_true", help="enable pycoway debug logging")
    parser.add_argument("--repeat", action="store_true", help="poll twice to show cache effect")
    args = parser.parse_args()
    return asyncio.run(run(debug=args.debug, repeat=args.repeat))


if __name__ == "__main__":
    raise SystemExit(main())
