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
    async_add_entities([
        PluggedBinarySensor(coordinator),
        ChargingSessionBinarySensor(coordinator),
        ChargingActiveBinarySensor(coordinator),
    ])


class _V2CBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base avec device_info commun."""

    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._ip_address = coordinator.ip_address

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
    def available(self):
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )


class PluggedBinarySensor(_V2CBinarySensorBase):
    """Voiture branchée — ON dès que ChargeState != 0 (waiting).

    Couvre aussi les états d'erreur (4, 5, 6) car le câble est physiquement
    branché dans ces cas.
    """

    _attr_translation_key = "plugged"

    @property
    def unique_id(self):
        return f"{self._ip_address}_plugged"

    @property
    def icon(self):
        return "mdi:power-plug" if self.is_on else "mdi:power-plug-off"

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        state = self.coordinator.data.get("ChargeState")
        if state is None:
            return None
        return state != 0


class ChargingSessionBinarySensor(_V2CBinarySensorBase):
    """Session de charge ouverte côté V2C — ON quand ChargeState == 2.

    Reste à ON même si la charge est en pause ou si le surplus solaire est
    insuffisant. Pour savoir si du courant passe réellement, utiliser
    ``charging_active`` (basé sur ChargePower).
    """

    _attr_translation_key = "charging_session"

    @property
    def unique_id(self):
        return f"{self._ip_address}_charging_session"

    @property
    def icon(self):
        return "mdi:car-electric" if self.is_on else "mdi:car-electric-outline"

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("ChargeState") == 2


class ChargingActiveBinarySensor(_V2CBinarySensorBase):
    """Charge réelle en cours — ON dès que ChargePower > 0.

    Contourne la limitation du V2 : ChargeState reste à 2 même quand le
    surplus solaire disparaît ou que la charge est en pause.
    """

    _attr_translation_key = "charging_active"

    @property
    def unique_id(self):
        return f"{self._ip_address}_charging_active"

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
