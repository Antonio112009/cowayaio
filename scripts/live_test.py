#!/usr/bin/env python3
"""Live smoke test against the real Coway IoCare API.

Credentials come from COWAY_EMAIL / COWAY_PASSWORD environment variables,
or from a `.env` file in the repo root (already gitignored):

    # .env
    COWAY_EMAIL=you@example.com
    COWAY_PASSWORD=...

    .venv/bin/python scripts/live_test.py

The .env file is parsed literally by this script (no shell involved), so
passwords with $, quotes, spaces, etc. are safe as-is — do NOT `source` it.

Options:
    --debug     enable pycoway debug logging (verbose, includes payloads)
    --repeat    poll twice to show warm-cache timing
    --env-file  path to the env file (default: <repo root>/.env)
"""

import argparse
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pycoway import CowayClient, CowayPurifier  # noqa: E402


def _load_env_file(path: str) -> None:
    """Load KEY=value pairs into os.environ, without shell expansion.

    Real environment variables take precedence. Values may optionally be
    wrapped in single or double quotes; everything else is literal.
    """
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().removeprefix("export ").strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key, value)


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


async def run(debug: bool, repeat: bool, env_file: str) -> int:
    _load_env_file(env_file)
    email = os.environ.get("COWAY_EMAIL")
    password = os.environ.get("COWAY_PASSWORD")
    if not email or not password:
        print("Set COWAY_EMAIL and COWAY_PASSWORD (env vars or .env file).", file=sys.stderr)
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
    repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug", action="store_true", help="enable pycoway debug logging")
    parser.add_argument("--repeat", action="store_true", help="poll twice to show cache effect")
    parser.add_argument(
        "--env-file",
        default=os.path.join(repo_root, ".env"),
        help="path to env file with COWAY_EMAIL/COWAY_PASSWORD",
    )
    args = parser.parse_args()
    return asyncio.run(run(debug=args.debug, repeat=args.repeat, env_file=args.env_file))


if __name__ == "__main__":
    raise SystemExit(main())
