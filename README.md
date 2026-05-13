# V2C Trydan Plus

Custom Home Assistant integration for V2C Trydan EV charger.

## Features

- All sensors from `/RealTimeData`
- **Switches**: Paused, Dynamic, Locked, Timer, PauseDynamic
- **Numbers**: MinIntensity, MaxIntensity, Intensity, ContractedPower, LightLED, LogoLED, ContractedPowerSolaire, ContractedPowerReseau
- **Select**: DynamicPowerMode (auto-sets ContractedPower based on mode)

## Installation via HACS

1. In HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category: Integration
3. Install "V2C Trydan Plus"
4. Restart Home Assistant
5. Add integration: Settings → Devices & Services → Add Integration → V2C Trydan Plus

## ContractedPower logic

When changing DynamicPowerMode:
- **PV exclusive** → sends `ContractedPowerSolaire` value (negative = export limit)
- **Min power / Grid+FV** → sends `ContractedPowerReseau` value
- **Other modes** → ContractedPower unchanged
