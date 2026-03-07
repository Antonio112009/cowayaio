"""Data-fetching layer for Coway IoCare purifiers."""

import json
import logging
from typing import Any

from pycoway.account.maintenance import CowayMaintenanceClient
from pycoway.constants import (
    CATEGORY_NAME,
    Endpoint,
    Header,
)
from pycoway.devices.models import CowayPurifier, DeviceAttributes, PurifierData
from pycoway.devices.parser import (
    build_filter_dict,
    build_purifier,
    extract_parsed_info,
    parse_purifier_html,
)
from pycoway.exceptions import (
    AuthError,
    CowayError,
    NoPurifiers,
)

LOGGER = logging.getLogger(__name__)


class CowayDataClient(CowayMaintenanceClient):
    """Fetches purifier inventories, filter status, and timer data."""

    async def async_get_purifiers(self) -> list[dict[str, Any]]:
        """Get all purifiers linked to Coway account."""

        if not self.places:
            LOGGER.debug(f"No places loaded. Doing initial login for {self.username}")
            await self.login()

        params = {"pageIndex": "0", "pageSize": "100"}
        headers = await self._create_endpoint_header()
        purifiers: list[dict[str, Any]] = []

        for place in self.places:
            LOGGER.debug(
                f"Checking place for {self.username}. "
                f"Place ID: {place.get('placeId')}, "
                f"Place Name: {place.get('placeName')}, "
                f"Device Count: {place.get('deviceCnt')}"
            )
            if place["deviceCnt"] == 0:
                continue

            url = f"{Endpoint.BASE_URI}{Endpoint.PLACES}/{place['placeId']}/devices"
            LOGGER.debug(f"Fetching devices for {self.username}. URL: {url}")

            try:
                response = await self._get_endpoint(url, headers, params)
            except AuthError:
                LOGGER.debug("Access and refresh tokens are invalid. Fetching new tokens.")
                await self.login()
                headers = await self._create_endpoint_header()
                response = await self._get_endpoint(url, headers, params)

            if "error" in response:
                raise CowayError(
                    f"Failed to get devices for Place ID: {place.get('placeId')} "
                    f"Response: {response['error']}"
                )

            devices = response.get("data", {}).get("content")
            if devices:
                purifiers.extend(d for d in devices if d["categoryName"] == CATEGORY_NAME)
            else:
                LOGGER.debug(
                    f"No devices at Place ID: {place.get('placeId')}, "
                    f"Place Name: {place.get('placeName')}"
                )

        return purifiers

    async def async_get_purifiers_data(self) -> PurifierData:
        """Return dataclass with all Purifier Devices."""

        LOGGER.debug(f"Getting purifiers data for {self.username}")
        if not self.places:
            LOGGER.debug(f"No places loaded. Doing initial login for {self.username}")
            await self.login()

        purifiers = await self.async_get_purifiers()
        LOGGER.debug(f"Purifiers found for {self.username}: {json.dumps(purifiers, indent=4)}")
        if not purifiers:
            raise NoPurifiers(
                f"No purifiers found for any IoCare+ places associated with {self.username}."
            )

        # Only check the token once for the entire batch.
        self.check_token = False
        LOGGER.debug("self.check_token set to False for batch processing.")

        try:
            await self.async_server_maintenance_notice()

            device_data: dict[str, CowayPurifier] = {}
            for dev in purifiers:
                nick = dev.get("dvcNick")
                LOGGER.debug(f"Building CowayPurifier for {nick}")

                purifier_html = await self._get_purifier_html(
                    dev["dvcNick"],
                    dev["deviceSerial"],
                    dev["modelCode"],
                    dev["placeId"],
                )
                purifier_info = parse_purifier_html(purifier_html, nick)
                if purifier_info is None:
                    LOGGER.debug(f"No purifier info found for {nick}. Skipping.")
                    continue
                parsed_info = extract_parsed_info(purifier_info)

                # Filter status
                LOGGER.debug(f"Fetching filter info for {nick}")
                filter_info = await self.async_fetch_filter_status(
                    dev["placeId"], dev["deviceSerial"], nick
                )
                parsed_info["filter_info"] = build_filter_dict(filter_info)
                LOGGER.debug(f"{nick} filter dict: {parsed_info['filter_info']}")

                # Timer
                LOGGER.debug(f"Fetching timer for {nick}")
                timer = await self.async_fetch_timer(dev["deviceSerial"], nick)
                parsed_info["timer_info"] = timer.get("offTimer")

                purifier = build_purifier(dev, parsed_info, raw_filters=filter_info)
                device_data[purifier.device_attr.device_id] = purifier
                LOGGER.debug(f"Finished CowayPurifier for {nick}")
        finally:
            self.check_token = True
            LOGGER.debug("self.check_token set back to True")

        all_purifiers = PurifierData(purifiers=device_data)
        LOGGER.debug(
            f"Final PurifierData for {self.username}: "
            f"{json.dumps(all_purifiers, default=vars, indent=4)}"
        )
        return all_purifiers

    async def async_fetch_filter_status(
        self, place_id: str, serial: str, name: str
    ) -> list[dict[str, Any]]:
        """Fetch Pre-filter and MAX2 filter states."""

        if self.check_token:
            await self._check_token()

        url = f"{Endpoint.SECONDARY_BASE}{Endpoint.PLACES}/{place_id}/devices/{serial}/supplies"
        headers = {
            "region": "NUS",
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
            "accept-language": Header.COWAY_LANGUAGE,
            "user-agent": Header.HTML_USER_AGENT,
        }
        params = {
            "membershipYn": "N",
            "membershipType": "",
            "langCd": Header.ACCEPT_LANG,
        }

        response = await self._get_endpoint(url, headers, params)
        if "error" in response:
            raise CowayError(
                f"Failed to get filter status for purifier {name}: {response['error']}"
            )
        return response.get("data", {}).get("suppliesList", [])

    async def async_fetch_timer(self, serial: str, name: str) -> dict[str, Any]:
        """Get the current timer setting."""

        if self.check_token:
            await self._check_token()

        url = f"{Endpoint.SECONDARY_BASE}{Endpoint.AIR}/{serial}/timer"
        headers = {
            "region": "NUS",
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
            "accept-language": Header.COWAY_LANGUAGE,
            "user-agent": Header.HTML_USER_AGENT,
        }

        response = await self._get_endpoint(url, headers, None)
        if "error" in response:
            raise CowayError(f"Failed to get timer for purifier {name}: {response['error']}")
        return response.get("data", {})

    # ------------------------------------------------------------------
    # IoT JSON API methods
    # ------------------------------------------------------------------

    @staticmethod
    def _hb_device_params(attr: DeviceAttributes) -> dict[str, str]:
        """Build the query-string params the IoT API endpoints require."""
        return {
            "devId": attr.device_id or "",
            "mqttDevice": str(attr.mqtt_device).lower(),
            "dvcBrandCd": attr.dvc_brand_cd or "",
            "dvcTypeCd": attr.dvc_type_cd or "",
            "prodName": attr.prod_name or "",
            "orderNo": attr.order_no or "",
            "membershipYn": "N",
            "selfYn": attr.self_manage_yn or "N",
            "sellTypeCd": attr.sell_type_cd or "",
        }

    async def async_get_hb_device_control(self, attr: DeviceAttributes) -> dict[str, Any]:
        """Fetch device control/status data via the IoT JSON API."""

        url = f"{Endpoint.HB_BASE_URI}{Endpoint.HB_DEVICE_CONTROL}/{attr.device_id}/control"
        params = self._hb_device_params(attr)
        response = await self._get_hb_endpoint(url, params)
        if "error" in response:
            raise CowayError(f"IoT control-status failed for {attr.name}: {response['error']}")
        return response.get("data", {})

    async def async_get_hb_air_home(self, attr: DeviceAttributes) -> dict[str, Any]:
        """Fetch air-quality home data via the IoT JSON API."""

        url = f"{Endpoint.HB_BASE_URI}{Endpoint.HB_AIR_HOME}/{attr.device_id}/home"
        params = self._hb_device_params(attr)
        response = await self._get_hb_endpoint(url, params)
        if "error" in response:
            raise CowayError(f"IoT air home failed for {attr.name}: {response['error']}")
        return response.get("data", {})

    async def async_get_hb_filter_info(self, attr: DeviceAttributes) -> dict[str, Any]:
        """Fetch filter info via the IoT JSON API."""

        url = f"{Endpoint.HB_BASE_URI}{Endpoint.HB_AIR_FILTER_INFO}/{attr.device_id}/filter-info"
        params = self._hb_device_params(attr)
        response = await self._get_hb_endpoint(url, params)
        if "error" in response:
            raise CowayError(f"IoT filter info failed for {attr.name}: {response['error']}")
        return response.get("data", {})

    async def async_get_hb_device_conn(self, attr: DeviceAttributes) -> dict[str, Any]:
        """Fetch device connection status via the IoT JSON API."""

        url = f"{Endpoint.HB_BASE_URI}{Endpoint.HB_DEVICE_CONN}"
        params = self._hb_device_params(attr)
        response = await self._get_hb_endpoint(url, params)
        if "error" in response:
            raise CowayError(f"IoT device connection failed for {attr.name}: {response['error']}")
        return response.get("data", {})
