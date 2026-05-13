"""Binary sensors for V2C Trydan."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up V2C Trydan binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ChargingActiveBinarySensor(coordinator)])


class ChargingActiveBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """True charging state based on actual power draw.

    ChargeState reste à 2 (session) même si la charge est en pause ou si le
    surplus solaire est insuffisant. Ce binary_sensor reflète la réalité :
    ON dès que ChargePower > 0, OFF sinon.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "charging_active"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._ip_address = coordinator.ip_address

    @property
    def unique_id(self):
        return "v2c_trydan_charging_active"

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
        return "mdi:flash" if self.is_on else "mdi:flash-off"

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        try:
            return float(self.coordinator.data.get("ChargePower", 0)) > 0
        except (ValueError, TypeError):
            return None

    @property
    def available(self):
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )
