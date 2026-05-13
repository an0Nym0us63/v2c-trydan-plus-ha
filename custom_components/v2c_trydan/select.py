from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er
import logging
import aiohttp
import asyncio
import json
import re

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DYNAMIC_POWER_MODE_OPTIONS = [
    "enable_timed_power",                    # 0 → rien
    "disable_timed_power",                   # 1 → rien
    "disable_timed_power_exclusive",         # 2 → contracted_power_solaire
    "disable_timed_power_min",               # 3 → contracted_power_reseau
    "disable_timed_power_grid_fv",           # 4 → contracted_power_reseau
    "disable_timed_power_stop",              # 5 → rien
]

# Mapping mode → unique_id du number à utiliser (None = ne rien envoyer)
CONTRACTED_POWER_MAP = {
    "disable_timed_power_exclusive": "v2c_trydan_plus_contracted_power_solaire",
    "disable_timed_power_min":       "v2c_trydan_plus_contracted_power_reseau",
    "disable_timed_power_grid_fv":   "v2c_trydan_plus_contracted_power_reseau",
}


def _parse_response_json(text: str, content_type: str = '') -> dict:
    if content_type and 'application/json' not in content_type.lower():
        _LOGGER.debug(f"Device returned non-JSON content-type: {content_type}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        firmware_pattern = r'"FirmwareVersion":"[^"]*",'
        matches = list(re.finditer(firmware_pattern, text))
        if len(matches) > 1:
            for match in matches[:-1]:
                text = text[:match.start()] + text[match.end():]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Failed to parse malformed JSON: {e}")
            raise


async def _write_value(hass, ip_address: str, keyword: str, value) -> None:
    session = async_get_clientsession(hass)
    url = f"http://{ip_address}/write/{keyword}={value}"
    try:
        timeout = aiohttp.ClientTimeout(total=5, connect=2)
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            response_text = await response.text()
            if response_text.strip().upper() == "ERROR":
                _LOGGER.error(f"Device returned ERROR when setting {keyword}={value}")
                raise ValueError(f"Device rejected {keyword}={value}")
    except asyncio.TimeoutError as err:
        _LOGGER.error(f"Timeout setting {keyword}: {err}")
        raise
    except aiohttp.ClientError as err:
        _LOGGER.error(f"HTTP error setting {keyword}: {err}")
        raise
    except Exception as err:
        _LOGGER.error(f"Unexpected error setting {keyword}: {err}")
        raise


def _get_state_by_unique_id(hass, unique_id: str):
    """Resolve entity state from unique_id — reliable regardless of entity_id naming."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("number", DOMAIN, unique_id)
    if entity_id is None:
        _LOGGER.warning(f"No entity found for unique_id '{unique_id}'")
        return None
    return hass.states.get(entity_id)


async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    async_add_entities([DynamicPowerModeSelect(hass, ip_address)])


class DynamicPowerModeSelect(SelectEntity):
    """Dynamic power mode selector.

    Rules for ContractedPower:
    - PV exclusive (2)  → send contracted_power_solaire
    - Min power (3)     → send contracted_power_reseau
    - Grid+FV (4)       → send contracted_power_reseau
    - All others        → do not touch ContractedPower
    """

    def __init__(self, hass, ip_address):
        self._hass = hass
        self._ip_address = ip_address
        self._current_option = None
        self._attr_has_entity_name = True
        self._attr_options = DYNAMIC_POWER_MODE_OPTIONS
        self._attr_translation_key = "dynamic_power_mode"

    @property
    def unique_id(self):
        return "v2c_trydan_plus_dynamic_power_mode_select"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._ip_address)},
            name=f"V2C Trydan ({self._ip_address})",
            manufacturer="V2C",
            model="Trydan",
            configuration_url=f"http://{self._ip_address}",
        )

    @property
    def icon(self):
        return "mdi:cog"

    @property
    def current_option(self):
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            _LOGGER.error(f"Invalid DynamicPowerMode option: {option}")
            return

        mode_value = self._attr_options.index(option)

        # 1. Set DynamicPowerMode on device
        await _write_value(self._hass, self._ip_address, "DynamicPowerMode", mode_value)

        # 2. Optionally set ContractedPower
        contracted_unique_id = CONTRACTED_POWER_MAP.get(option)
        if contracted_unique_id is not None:
            state = _get_state_by_unique_id(self._hass, contracted_unique_id)
            if state is not None:
                try:
                    contracted_value = int(float(state.state))
                    await _write_value(self._hass, self._ip_address, "ContractedPower", contracted_value)
                    _LOGGER.debug(f"Mode '{option}': ContractedPower set to {contracted_value} W")
                except (ValueError, TypeError) as e:
                    _LOGGER.error(f"Could not parse value from '{contracted_unique_id}': {e}")
            else:
                _LOGGER.warning(f"Entity '{contracted_unique_id}' not found, ContractedPower not updated")
        else:
            _LOGGER.debug(f"Mode '{option}': ContractedPower not changed")

        self._current_option = option
        self.async_write_ha_state()

    async def async_update(self):
        if not self._ip_address:
            return
        session = async_get_clientsession(self._hass)
        url = f"http://{self._ip_address}/RealTimeData"
        try:
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            async with session.get(url, timeout=timeout) as response:
                response.raise_for_status()
                text = await response.text()
                content_type = response.headers.get('content-type', '')
                data = _parse_response_json(text, content_type)
                dynamic_power_mode = data.get("DynamicPowerMode")
                if dynamic_power_mode is not None and 0 <= dynamic_power_mode <= 5:
                    self._current_option = self._attr_options[dynamic_power_mode]
                else:
                    _LOGGER.warning(f"Invalid DynamicPowerMode value: {dynamic_power_mode}")
        except (asyncio.TimeoutError, aiohttp.ClientError, ValueError) as err:
            _LOGGER.error(f"Error fetching dynamic power mode: {err}")
        except Exception as err:
            _LOGGER.error(f"Unexpected error fetching dynamic power mode: {err}")
