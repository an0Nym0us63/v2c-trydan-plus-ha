"""The v2c_trydan component."""
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.helpers import device_registry as dr, config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging
import aiohttp

from .const import DOMAIN
from .coordinator import V2CtrydanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT, Platform.BINARY_SENSOR]

# Configuration schema - this integration is config entry only
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    for entry_config in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=entry_config
            )
        )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up V2C Trydan from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    ip_address = entry.data[CONF_IP_ADDRESS]
    
    # Create the coordinator
    coordinator = V2CtrydanDataUpdateCoordinator(hass, ip_address)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store the coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Register device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.ip_address)},
        manufacturer="V2C",
        model="Trydan",
        name=f"V2C Trydan ({coordinator.ip_address})",
        configuration_url=f"http://{coordinator.ip_address}",
    )
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services once (multiple entries reuse the same handlers).
    _register_services(hass)

    return True


_SERVICE_NAMES = (
    "set_min_intensity",
    "set_max_intensity",
    "set_intensity",
    "set_dynamic_power_mode",
    "set_min_intensity_slider",
    "set_max_intensity_slider",
    "set_dynamic_power_mode_slider",
)


def _first_coordinator(hass: HomeAssistant):
    """Return any coordinator (first entry). Suffisant tant qu'on a 1 seul device."""
    data = hass.data.get(DOMAIN, {})
    for coord in data.values():
        if hasattr(coord, "ip_address"):
            return coord
    return None


def _register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, "set_min_intensity"):
        return

    async def _svc_set_min_intensity(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("min_intensity"))
        except (TypeError, ValueError):
            _LOGGER.error("min_intensity must be an integer")
            return
        if not 6 <= value <= 32:
            _LOGGER.error("min_intensity must be between 6 and 32")
            return
        await async_set_min_intensity(hass, coord.ip_address, value)

    async def _svc_set_max_intensity(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("max_intensity"))
        except (TypeError, ValueError):
            _LOGGER.error("max_intensity must be an integer")
            return
        if not 6 <= value <= 32:
            _LOGGER.error("max_intensity must be between 6 and 32")
            return
        await async_set_max_intensity(hass, coord.ip_address, value)

    async def _svc_set_intensity(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("intensity"))
        except (TypeError, ValueError):
            _LOGGER.error("intensity must be an integer")
            return
        if not 6 <= value <= 32:
            _LOGGER.error("intensity must be between 6 and 32")
            return
        await async_set_intensity(hass, coord.ip_address, value)

    async def _svc_set_dynamic_power_mode(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("DynamicPowerMode"))
        except (TypeError, ValueError):
            _LOGGER.error("DynamicPowerMode must be an integer")
            return
        if not 0 <= value <= 5:
            _LOGGER.error("DynamicPowerMode must be between 0 and 5")
            return
        # NB: call the module-level HTTP helper, not the service handler.
        await async_set_dynamic_power_mode(hass, coord.ip_address, value)

    # Legacy "_slider" variants — same handler, different parameter name.
    async def _svc_set_min_intensity_slider(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("v2c_min_intensity"))
        except (TypeError, ValueError):
            return
        if not 6 <= value <= 32:
            return
        await async_set_min_intensity(hass, coord.ip_address, value)

    async def _svc_set_max_intensity_slider(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("v2c_max_intensity"))
        except (TypeError, ValueError):
            return
        if not 6 <= value <= 32:
            return
        await async_set_max_intensity(hass, coord.ip_address, value)

    async def _svc_set_dynamic_power_mode_slider(call: ServiceCall):
        coord = _first_coordinator(hass)
        if coord is None:
            return
        try:
            value = int(call.data.get("v2c_dynamic_power_mode"))
        except (TypeError, ValueError):
            return
        if not 0 <= value <= 5:
            return
        await async_set_dynamic_power_mode(hass, coord.ip_address, value)

    hass.services.async_register(DOMAIN, "set_min_intensity", _svc_set_min_intensity)
    hass.services.async_register(DOMAIN, "set_max_intensity", _svc_set_max_intensity)
    hass.services.async_register(DOMAIN, "set_intensity", _svc_set_intensity)
    hass.services.async_register(DOMAIN, "set_dynamic_power_mode", _svc_set_dynamic_power_mode)
    hass.services.async_register(DOMAIN, "set_min_intensity_slider", _svc_set_min_intensity_slider)
    hass.services.async_register(DOMAIN, "set_max_intensity_slider", _svc_set_max_intensity_slider)
    hass.services.async_register(DOMAIN, "set_dynamic_power_mode_slider", _svc_set_dynamic_power_mode_slider)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # When the last entry is gone, remove our services.
        if not hass.data[DOMAIN]:
            for name in _SERVICE_NAMES:
                if hass.services.has_service(DOMAIN, name):
                    hass.services.async_remove(DOMAIN, name)

    return unload_ok

async def async_set_min_intensity(hass: HomeAssistant, ip_address: str, min_intensity: int):
    """Set minimum charging intensity."""
    session = async_get_clientsession(hass)
    url = f"http://{ip_address}/write/MinIntensity={min_intensity}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            _LOGGER.debug(f"Min intensity set to {min_intensity} at {ip_address}")
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error setting min intensity: {err}")

async def async_set_max_intensity(hass: HomeAssistant, ip_address: str, max_intensity: int):
    """Set maximum charging intensity."""
    session = async_get_clientsession(hass)
    url = f"http://{ip_address}/write/MaxIntensity={max_intensity}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            _LOGGER.debug(f"Max intensity set to {max_intensity} at {ip_address}")
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error setting max intensity: {err}")

async def async_set_dynamic_power_mode(hass: HomeAssistant, ip_address: str, dynamic_power_mode: int):
    """Set dynamic power mode."""
    session = async_get_clientsession(hass)
    url = f"http://{ip_address}/write/DynamicPowerMode={dynamic_power_mode}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            _LOGGER.debug(f"Dynamic power mode set to {dynamic_power_mode} at {ip_address}")
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error setting dynamic power mode: {err}")

async def async_set_intensity(hass: HomeAssistant, ip_address: str, intensity: int):
    """Set charging intensity."""
    session = async_get_clientsession(hass)
    url = f"http://{ip_address}/write/Intensity={intensity}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            _LOGGER.debug(f"Intensity set to {intensity} at {ip_address}")
    except aiohttp.ClientError as err:
        _LOGGER.error(f"Error setting intensity: {err}")
