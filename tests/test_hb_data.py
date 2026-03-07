"""Tests for IoT JSON API data methods and extract_hb_parsed_info parser."""

from unittest.mock import AsyncMock

import pytest

from pycoway.constants import Endpoint
from pycoway.devices.data import CowayDataClient
from pycoway.devices.models import DeviceAttributes
from pycoway.devices.parser import extract_hb_parsed_info
from pycoway.exceptions import CowayError


@pytest.fixture
def hb_device_attr() -> DeviceAttributes:
    """DeviceAttributes populated with IoT API discovery fields."""
    return DeviceAttributes(
        device_id="15902EUZ2282500520",
        model="AIRMEGA 300s/400s",
        model_code="AP-2015E(GRAPHITE_US)",
        code="02EUZ",
        name="HH AIR PURIFIER",
        product_name="AIRMEGA",
        place_id=None,
        dvc_brand_cd="MG",
        dvc_type_cd="004",
        prod_name="AIRMEGA",
        prod_name_full="AIRMEGA 300s/400s",
        order_no="ORD1WBGmBa7P",
        sell_type_cd="1",
        admdong_cd="GB",
        station_cd="GB",
        self_manage_yn="N",
        mqtt_device=True,
    )


class TestHBDeviceParams:
    def test_builds_expected_params(self, hb_device_attr):
        params = CowayDataClient._hb_device_params(hb_device_attr)
        assert params["devId"] == "15902EUZ2282500520"
        assert params["mqttDevice"] == "true"
        assert params["dvcBrandCd"] == "MG"
        assert params["dvcTypeCd"] == "004"
        assert params["prodName"] == "AIRMEGA"
        assert params["orderNo"] == "ORD1WBGmBa7P"
        assert params["membershipYn"] == "N"
        assert params["selfYn"] == "N"
        assert params["sellTypeCd"] == "1"

    def test_defaults_for_minimal_attr(self):
        attr = DeviceAttributes(
            device_id="DEV1",
            model=None,
            model_code=None,
            code=None,
            name=None,
            product_name=None,
            place_id=None,
        )
        params = CowayDataClient._hb_device_params(attr)
        assert params["devId"] == "DEV1"
        assert params["mqttDevice"] == "false"
        assert params["dvcBrandCd"] == ""
        assert params["orderNo"] == ""


def _mock_hb_client(response: dict) -> CowayDataClient:
    """Create a CowayDataClient with a mocked _get_hb_endpoint."""
    client = CowayDataClient.__new__(CowayDataClient)
    client._get_hb_endpoint = AsyncMock(return_value=response)
    return client


class TestAsyncGetHBDeviceControl:
    async def test_returns_data(self, hb_device_attr):
        payload = {"controlStatusData": {"data": {"statusInfo": {"attributes": {"0001": 1}}}}}
        client = _mock_hb_client({"data": payload})
        result = await client.async_get_hb_device_control(hb_device_attr)
        assert result == payload

    async def test_correct_url(self, hb_device_attr):
        client = _mock_hb_client({"data": {}})
        await client.async_get_hb_device_control(hb_device_attr)
        call_args = client._get_hb_endpoint.call_args
        url = call_args[0][0]
        assert url == (
            f"{Endpoint.HB_BASE_URI}{Endpoint.HB_DEVICE_CONTROL}/15902EUZ2282500520/control"
        )

    async def test_raises_on_error(self, hb_device_attr):
        client = _mock_hb_client({"error": "unauthorized"})
        with pytest.raises(CowayError, match="IoT control-status failed"):
            await client.async_get_hb_device_control(hb_device_attr)


class TestAsyncGetHBAirHome:
    async def test_returns_data(self, hb_device_attr):
        payload = {"airHomeData": {"sensorInfo": {"attributes": {"0001": 10}}}}
        client = _mock_hb_client({"data": payload})
        result = await client.async_get_hb_air_home(hb_device_attr)
        assert result == payload

    async def test_correct_url(self, hb_device_attr):
        client = _mock_hb_client({"data": {}})
        await client.async_get_hb_air_home(hb_device_attr)
        url = client._get_hb_endpoint.call_args[0][0]
        assert url == (f"{Endpoint.HB_BASE_URI}{Endpoint.HB_AIR_HOME}/15902EUZ2282500520/home")

    async def test_raises_on_error(self, hb_device_attr):
        client = _mock_hb_client({"error": "server error"})
        with pytest.raises(CowayError, match="IoT air home failed"):
            await client.async_get_hb_air_home(hb_device_attr)


class TestAsyncGetHBFilterInfo:
    async def test_returns_data(self, hb_device_attr):
        payload = {"suppliesList": [{"supplyNm": "MAX2 Filter", "filterRemain": 72}]}
        client = _mock_hb_client({"data": payload})
        result = await client.async_get_hb_filter_info(hb_device_attr)
        assert result == payload

    async def test_correct_url(self, hb_device_attr):
        client = _mock_hb_client({"data": {}})
        await client.async_get_hb_filter_info(hb_device_attr)
        url = client._get_hb_endpoint.call_args[0][0]
        assert url == (
            f"{Endpoint.HB_BASE_URI}{Endpoint.HB_AIR_FILTER_INFO}/15902EUZ2282500520/filter-info"
        )

    async def test_raises_on_error(self, hb_device_attr):
        client = _mock_hb_client({"error": "not found"})
        with pytest.raises(CowayError, match="IoT filter info failed"):
            await client.async_get_hb_filter_info(hb_device_attr)


class TestAsyncGetHBDeviceConn:
    async def test_returns_data(self, hb_device_attr):
        payload = {"netStatus": "online"}
        client = _mock_hb_client({"data": payload})
        result = await client.async_get_hb_device_conn(hb_device_attr)
        assert result == payload

    async def test_correct_url(self, hb_device_attr):
        client = _mock_hb_client({"data": {}})
        await client.async_get_hb_device_conn(hb_device_attr)
        url = client._get_hb_endpoint.call_args[0][0]
        assert url == f"{Endpoint.HB_BASE_URI}{Endpoint.HB_DEVICE_CONN}"

    async def test_raises_on_error(self, hb_device_attr):
        client = _mock_hb_client({"error": "timeout"})
        with pytest.raises(CowayError, match="IoT device connection failed"):
            await client.async_get_hb_device_conn(hb_device_attr)


class TestExtractHBParsedInfo:
    def test_full_response(self):
        control = {
            "controlStatusData": {
                "data": {
                    "statusInfo": {"attributes": {"0001": 1, "0002": 1, "0003": 2, "0008": 120}}
                },
                "coreData": [{"data": {"currentMcuVer": "3.1.0"}}],
            }
        }
        air = {
            "airHomeData": {
                "sensorInfo": {"attributes": {"0001": 12, "0002": 20}},
                "iaqGrade": 2,
            }
        }
        conn = {"netStatus": "online"}

        result = extract_hb_parsed_info(control, air, conn)

        assert result["status_info"] == {"0001": 1, "0002": 1, "0003": 2, "0008": 120}
        assert result["mcu_info"] == {"currentMcuVer": "3.1.0"}
        assert result["sensor_info"] == {"0001": 12, "0002": 20}
        assert result["aq_grade"] == {"iaqGrade": 2}
        assert result["network_info"] == {"wifiConnected": True}
        assert result["timer_info"] == 120

    def test_offline_device(self):
        result = extract_hb_parsed_info({}, {}, {"netStatus": "offline"})
        assert result["network_info"] == {"wifiConnected": False}

    def test_empty_responses(self):
        result = extract_hb_parsed_info({}, {}, {})
        assert result["status_info"] == {}
        assert result["mcu_info"] == {}
        assert result["sensor_info"] == {}
        assert result["device_info"] == {}
        assert result["filter_info"] == {}
        assert result["timer_info"] is None

    def test_no_iaq_grade(self):
        air = {"airHomeData": {"sensorInfo": {"attributes": {"0001": 5}}}}
        result = extract_hb_parsed_info({}, air, {})
        assert result["aq_grade"] == {}
        assert result["sensor_info"] == {"0001": 5}
