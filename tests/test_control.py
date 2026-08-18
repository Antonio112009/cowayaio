"""Tests for purifier control commands."""

from unittest.mock import AsyncMock

import pytest

from pycoway.constants import CommandCode, LightMode
from pycoway.devices.control import CowayControlClient
from pycoway.exceptions import CowayError


def _mock_control_client(response) -> CowayControlClient:
    """Create a CowayControlClient with a mocked async_control_purifier."""
    client = CowayControlClient.__new__(CowayControlClient)
    client.async_control_purifier = AsyncMock(return_value=response)
    return client


class TestSetLightMode:
    async def test_sends_string_wire_value(self, sample_device):
        client = _mock_control_client({"header": {}})
        await client.async_set_light_mode(sample_device, LightMode.OFF)
        client.async_control_purifier.assert_awaited_once_with(
            sample_device, CommandCode.LIGHT, "2"
        )

    async def test_accepts_string_value(self, sample_device):
        client = _mock_control_client({"header": {}})
        await client.async_set_light_mode(sample_device, "1")
        client.async_control_purifier.assert_awaited_once_with(
            sample_device, CommandCode.LIGHT, "1"
        )

    async def test_error_response_raises(self, sample_device):
        client = _mock_control_client({"header": {"error_code": "E1", "error_text": "bad"}})
        with pytest.raises(CowayError, match="light mode"):
            await client.async_set_light_mode(sample_device, LightMode.ON)


class TestSetLight:
    async def test_on_off_wire_values(self, sample_device):
        client = _mock_control_client({"header": {}})
        await client.async_set_light(sample_device, True)
        client.async_control_purifier.assert_awaited_with(sample_device, CommandCode.LIGHT, "2")
        await client.async_set_light(sample_device, False)
        client.async_control_purifier.assert_awaited_with(sample_device, CommandCode.LIGHT, "0")


class TestSetFanSpeed:
    async def test_invalid_speed_raises(self, sample_device):
        client = _mock_control_client({"header": {}})
        with pytest.raises(CowayError, match="Invalid fan speed"):
            await client.async_set_fan_speed(sample_device, "5")
        client.async_control_purifier.assert_not_awaited()
