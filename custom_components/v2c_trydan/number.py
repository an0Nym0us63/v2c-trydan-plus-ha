from homeassistant.components.number import NumberEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import DEVICE_DEFAULT_NAME, CONF_IP_ADDRESS
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import logging
import aiohttp
import asyncio

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    ip_address = config_entry.data[CONF_IP_ADDRESS]
    _LOGGER.info(f"Setting up number entities with IP address: {ip_address}")

    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([
        MaxIntensityNumber(coordinator),
        MinIntensityNumber(coordinator),
        IntensityNumber(coordinator),
        MaxPrice(hass, ip_address),
        ContractedPowerNumber(coordinator),
        ContractedPowerSolaireNumber(hass, ip_address),
        ContractedPowerReseauNumber(hass, ip_address),
        LightLEDNumber(coordinator),
        LogoLEDNumber(coordinator),
    ])


async def _write_value(hass, ip_address: str, keyword: str, value) -> None:
    """Send a write command to the V2C device."""
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


class MaxIntensityNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ip_address = coordinator.ip_address
        self._attr_has_entity_name = True
        self._attr_translation_key = "max_intensity"

    @property
    def unique_id(self): return "v2c_trydan_max_intensity"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:gauge-full"

    @property
    def native_unit_of_measurement(self): return "A"

    @property
    def native_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('MaxIntensity', 32)
        return 32

    @property
    def native_max_value(self): return 32

    @property
    def native_min_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('MinIntensity', 6)
        return 6

    @property
    def state_class(self): return SensorStateClass.MEASUREMENT

    async def async_set_native_value(self, value):
        int_value = int(value)
        if self.native_min_value <= int_value <= self.native_max_value:
            await _write_value(self.hass, self._ip_address, "MaxIntensity", int_value)
            await self._coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"v2c_max_intensity must be between {self.native_min_value} and {self.native_max_value}")


class MinIntensityNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ip_address = coordinator.ip_address
        self._attr_has_entity_name = True
        self._attr_translation_key = "min_intensity"

    @property
    def unique_id(self): return "v2c_trydan_min_intensity"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:gauge-low"

    @property
    def native_unit_of_measurement(self): return "A"

    @property
    def native_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('MinIntensity', 6)
        return 6

    @property
    def native_max_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('MaxIntensity', 32)
        return 32

    @property
    def native_min_value(self): return 6

    @property
    def state_class(self): return SensorStateClass.MEASUREMENT

    async def async_set_native_value(self, value):
        int_value = int(value)
        if self.native_min_value <= int_value <= self.native_max_value:
            await _write_value(self.hass, self._ip_address, "MinIntensity", int_value)
            await self._coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"v2c_min_intensity must be between {self.native_min_value} and {self.native_max_value}")


class IntensityNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ip_address = coordinator.ip_address
        self._attr_has_entity_name = True
        self._attr_translation_key = "intensity"

    @property
    def unique_id(self): return "v2c_trydan_intensity"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:current-ac"

    @property
    def native_unit_of_measurement(self): return "A"

    @property
    def native_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('Intensity', 6)
        return 6

    @property
    def native_max_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('MaxIntensity', 32)
        return 32

    @property
    def native_min_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get('MinIntensity', 6)
        return 6

    @property
    def state_class(self): return SensorStateClass.MEASUREMENT

    async def async_set_native_value(self, value):
        int_value = int(value)
        if self.native_min_value <= int_value <= self.native_max_value:
            await _write_value(self.hass, self._ip_address, "Intensity", int_value)
            await self._coordinator.async_request_refresh()
        else:
            _LOGGER.error(f"v2c_intensity must be between {self.native_min_value} and {self.native_max_value}")


class MaxPrice(NumberEntity, RestoreEntity):
    def __init__(self, hass, ip_address):
        self._hass = hass
        self._ip_address = ip_address
        self._state = 0
        self._attr_has_entity_name = True
        self._attr_translation_key = "max_price"

    @property
    def unique_id(self): return f"{self._ip_address}_MaxPrice"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:currency-eur"

    @property
    def native_value(self): return self._state

    @property
    def native_step(self): return 0.001

    @property
    def native_max_value(self): return 1.000

    @property
    def native_min_value(self): return 0.000

    @property
    def state_class(self): return SensorStateClass.MEASUREMENT

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = float(last_state.state)
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value):
        if 0 <= value <= 1.0:
            self._state = value
            self.async_write_ha_state()
        else:
            _LOGGER.error("v2c_MaxPrice must be between 0 and 1")


# ---------------------------------------------------------------------------
# New entities
# ---------------------------------------------------------------------------

class ContractedPowerNumber(CoordinatorEntity, NumberEntity):
    """Contracted power — reflects and writes the device value."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ip_address = coordinator.ip_address
        self._attr_has_entity_name = True
        self._attr_translation_key = "contracted_power"

    @property
    def unique_id(self): return "v2c_trydan_contracted_power"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:flash"

    @property
    def native_unit_of_measurement(self): return "W"

    @property
    def native_value(self):
        if self._coordinator.data:
            return self._coordinator.data.get("ContractedPower", 4600)
        return 4600

    @property
    def mode(self):
        from homeassistant.components.number import NumberMode
        return NumberMode.BOX

    @property
    def native_min_value(self): return -10000

    @property
    def native_max_value(self): return 30000

    @property
    def native_step(self): return 100

    @property
    def state_class(self): return SensorStateClass.MEASUREMENT

    async def async_set_native_value(self, value):
        await _write_value(self.hass, self._ip_address, "ContractedPower", int(value))
        await self._coordinator.async_request_refresh()


class ContractedPowerSolaireNumber(NumberEntity, RestoreEntity):
    """Local param: ContractedPower value to send when PV exclusive mode is selected (negative = export limit)."""

    def __init__(self, hass, ip_address):
        self._hass = hass
        self._ip_address = ip_address
        self._state = -100
        self._attr_has_entity_name = True
        self._attr_translation_key = "contracted_power_solaire"

    @property
    def unique_id(self): return "v2c_trydan_contracted_power_solaire"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:solar-power"

    @property
    def native_unit_of_measurement(self): return "W"

    @property
    def native_value(self): return self._state

    @property
    def mode(self):
        from homeassistant.components.number import NumberMode
        return NumberMode.BOX

    @property
    def native_min_value(self): return -10000

    @property
    def native_max_value(self): return 30000

    @property
    def native_step(self): return 100

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = int(float(last_state.state))
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value):
        self._state = int(value)
        self.async_write_ha_state()


class ContractedPowerReseauNumber(NumberEntity, RestoreEntity):
    """Local param: ContractedPower value to send when grid modes are selected."""

    def __init__(self, hass, ip_address):
        self._hass = hass
        self._ip_address = ip_address
        self._state = 4600
        self._attr_has_entity_name = True
        self._attr_translation_key = "contracted_power_reseau"

    @property
    def unique_id(self): return "v2c_trydan_contracted_power_reseau"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:transmission-tower"

    @property
    def native_unit_of_measurement(self): return "W"

    @property
    def native_value(self): return self._state

    @property
    def mode(self):
        from homeassistant.components.number import NumberMode
        return NumberMode.BOX

    @property
    def native_min_value(self): return -10000

    @property
    def native_max_value(self): return 30000

    @property
    def native_step(self): return 100

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = int(float(last_state.state))
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value):
        self._state = int(value)
        self.async_write_ha_state()


class LightLEDNumber(CoordinatorEntity, NumberEntity, RestoreEntity):
    """LED light intensity (0-100%). State is local — not in RealTimeData."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ip_address = coordinator.ip_address
        self._attr_has_entity_name = True
        self._attr_translation_key = "light_led"
        self._local_value = 100

    @property
    def unique_id(self): return "v2c_trydan_light_led"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:led-on"

    @property
    def native_unit_of_measurement(self): return "%"

    @property
    def native_value(self): return self._local_value

    @property
    def native_min_value(self): return 0

    @property
    def native_max_value(self): return 100

    @property
    def native_step(self): return 1

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._local_value = int(float(last_state.state))
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value):
        int_value = int(value)
        await _write_value(self.hass, self._ip_address, "LightLED", int_value)
        self._local_value = int_value
        self.async_write_ha_state()


class LogoLEDNumber(CoordinatorEntity, NumberEntity, RestoreEntity):
    """Logo LED intensity (0-100%). State is local — not in RealTimeData."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._ip_address = coordinator.ip_address
        self._attr_has_entity_name = True
        self._attr_translation_key = "logo_led"
        self._local_value = 100

    @property
    def unique_id(self): return "v2c_trydan_logo_led"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._ip_address)}, name=f"V2C Trydan ({self._ip_address})", manufacturer="V2C", model="Trydan", configuration_url=f"http://{self._ip_address}")

    @property
    def icon(self): return "mdi:led-outline"

    @property
    def native_unit_of_measurement(self): return "%"

    @property
    def native_value(self): return self._local_value

    @property
    def native_min_value(self): return 0

    @property
    def native_max_value(self): return 100

    @property
    def native_step(self): return 1

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._local_value = int(float(last_state.state))
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value):
        int_value = int(value)
        await _write_value(self.hass, self._ip_address, "LogoLED", int_value)
        self._local_value = int_value
        self.async_write_ha_state()
