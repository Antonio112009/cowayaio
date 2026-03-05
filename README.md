# cowayaio

[![CI](https://github.com/Antonio112009/cowayaio/actions/workflows/ci.yml/badge.svg)](https://github.com/Antonio112009/cowayaio/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.0-orange)](https://github.com/Antonio112009/cowayaio/releases)

An asynchronous Python library for the [Coway IoCare](https://iocare.com/) API, used to control Coway air purifiers (AIRMEGA series).

> **Fork notice:** This is a maintained fork of [RobertD502/cowayaio](https://github.com/RobertD502/cowayaio) with bug fixes, refactored architecture, typed models, tests, and CI.

## Features

- Async/await API built on [aiohttp](https://docs.aiohttp.org/)
- Automatic token management and session handling
- Typed dataclass models for purifier state
- Full control: power, fan speed, modes, light, timer
- Air quality readings: PM2.5, PM10, CO₂, AQI
- Filter status monitoring
- Async context manager for clean resource management

## Requirements

- Python 3.11+
- A Coway IoCare account with registered purifier(s)

## Installation

```bash
pip install cowayaio
```

## Quick Start

```python
import asyncio
from cowayaio import CowayClient, LightMode


async def main():
    async with CowayClient("email@example.com", "password") as client:
        await client.login()
        data = await client.async_get_purifiers_data()

        for device_id, purifier in data.purifiers.items():
            print(f"{purifier.device_attr.name} ({device_id})")
            print(f"  Power: {'On' if purifier.is_on else 'Off'}")
            print(f"  Fan Speed: {purifier.fan_speed}")
            print(f"  PM2.5: {purifier.particulate_matter_2_5}")
            print(f"  AQI: {purifier.air_quality_index}")


asyncio.run(main())
```

## Controlling a Purifier

All control methods take a `device_attr` object from a `CowayPurifier`:

```python
async with CowayClient("email@example.com", "password") as client:
    await client.login()
    data = await client.async_get_purifiers_data()

    purifier = list(data.purifiers.values())[0]
    attr = purifier.device_attr

    # Power on/off
    await client.async_set_power(attr, is_on=True)

    # Modes
    await client.async_set_auto_mode(attr)
    await client.async_set_night_mode(attr)
    await client.async_set_eco_mode(attr)       # AIRMEGA AP-1512HHS only
    await client.async_set_rapid_mode(attr)      # AIRMEGA 250s only

    # Fan speed (1, 2, or 3)
    await client.async_set_fan_speed(attr, speed="2")

    # Light
    await client.async_set_light(attr, light_on=True)
    await client.async_set_light_mode(attr, LightMode.OFF)

    # Timer (minutes: 0, 60, 120, 240, 480)
    await client.async_set_timer(attr, time="120")
```

## Available Data

Each `CowayPurifier` provides:

| Field | Type | Description |
|---|---|---|
| `device_attr` | `DeviceAttributes` | Device ID, model, name, place ID |
| `is_on` | `bool \| None` | Power state |
| `fan_speed` | `int \| None` | Fan speed (1–3) |
| `auto_mode` | `bool \| None` | Auto mode active |
| `night_mode` | `bool \| None` | Night mode active |
| `eco_mode` | `bool \| None` | Eco mode active |
| `rapid_mode` | `bool \| None` | Rapid mode active |
| `light_on` | `bool \| None` | Light on/off |
| `particulate_matter_2_5` | `int \| None` | PM2.5 reading |
| `particulate_matter_10` | `int \| None` | PM10 reading |
| `carbon_dioxide` | `int \| None` | CO₂ reading |
| `air_quality_index` | `int \| None` | AQI reading |
| `pre_filter_pct` | `int \| None` | Pre-filter remaining % |
| `max2_pct` | `int \| None` | MAX2 filter remaining % |

## Exceptions

All exceptions inherit from `CowayError` and can be imported directly from the package:

```python
from cowayaio import CowayError, AuthError, PasswordExpired
```

| Exception | Description |
|---|---|
| `CowayError` | Base exception for all library errors |
| `AuthError` | Authentication failure (invalid credentials) |
| `PasswordExpired` | Password needs changing (60+ days old) |
| `ServerMaintenance` | Coway API is under maintenance |
| `RateLimited` | Account temporarily blocked (wait 24 hours) |
| `NoPlaces` | No places configured in IoCare account |
| `NoPurifiers` | No purifiers found in account |

## Project Structure

```
src/cowayaio/
├── client.py              # Public CowayClient entry point
├── constants.py           # Enums: endpoints, parameters, headers
├── exceptions.py          # Exception hierarchy
├── account/               # Authentication & maintenance
├── devices/               # Purifier control, data, models, parsing
└── transport/             # HTTP session management
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, branch strategy, and guidelines.

## License

[MIT](LICENSE) — originally by [RobertD502](https://github.com/RobertD502)
