"""Sensors for Eurosat Meters: one sensor per meter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EurosatCoordinator

_TOTAL = SensorStateClass.TOTAL_INCREASING
_MEAS = SensorStateClass.MEASUREMENT

# API unit (lower-case) -> (HA unit, device class, state class)
UNIT_MAP: dict[str, tuple[str, SensorDeviceClass | None, SensorStateClass]] = {
    "kwh": (UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, _TOTAL),
    "wh": (UnitOfEnergy.WATT_HOUR, SensorDeviceClass.ENERGY, _TOTAL),
    "mwh": (UnitOfEnergy.MEGA_WATT_HOUR, SensorDeviceClass.ENERGY, _TOTAL),
    "m3": (UnitOfVolume.CUBIC_METERS, SensorDeviceClass.WATER, _TOTAL),
    "m³": (UnitOfVolume.CUBIC_METERS, SensorDeviceClass.WATER, _TOTAL),
    "l": (UnitOfVolume.LITERS, SensorDeviceClass.WATER, _TOTAL),
    "°c": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, _MEAS),
    "v": (UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, _MEAS),
    "kg": (UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT, _MEAS),
    "%": (PERCENTAGE, None, _MEAS),
}


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create a sensor per meter; add new meters as they appear."""
    coordinator: EurosatCoordinator = entry.runtime_data
    known: set[int] = set()

    @callback
    def _add_new() -> None:
        new = [mid for mid in coordinator.data if mid not in known]
        if new:
            known.update(new)
            async_add_entities(
                EurosatMeterSensor(coordinator, entry.entry_id, mid) for mid in new
            )

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class EurosatMeterSensor(CoordinatorEntity[EurosatCoordinator], SensorEntity):
    """Last known reading of a single meter."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EurosatCoordinator, entry_id: str, meter_id: int
    ) -> None:
        super().__init__(coordinator)
        self._meter_id = meter_id
        row = coordinator.data[meter_id]

        self._attr_unique_id = f"{entry_id}_{meter_id}"
        self._attr_name = coordinator.titles.get(meter_id) or f"Meter {meter_id}"

        raw_unit = str(row.get("measure_unit") or "").strip()
        unit, device_class, state_class = UNIT_MAP.get(
            raw_unit.lower(), (raw_unit or None, None, _MEAS)
        )
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if device_class in (SensorDeviceClass.ENERGY, SensorDeviceClass.WATER):
            self._attr_suggested_display_precision = 2

        imei = row.get("gps_unit_imei") or str(row.get("gps_unit_id"))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(row.get("gps_unit_id") or imei))},
            name=f"Eurosat {imei}",
            manufacturer="Eurosat",
            serial_number=imei,
        )

    @property
    def _row(self) -> dict[str, Any] | None:
        return self.coordinator.data.get(self._meter_id)

    @property
    def available(self) -> bool:
        return super().available and self._row is not None

    @property
    def native_value(self) -> float | None:
        row = self._row
        value = row.get("value") if row else None
        return value if isinstance(value, (int, float)) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        row = self._row or {}
        attrs: dict[str, Any] = {
            "meter_id": self._meter_id,
            "gps_unit_id": row.get("gps_unit_id"),
            "gps_unit_imei": row.get("gps_unit_imei"),
        }
        if isinstance(row.get("time"), (int, float)):
            attrs["measured_at"] = datetime.fromtimestamp(
                row["time"], tz=timezone.utc
            ).isoformat()
        if row.get("probe_sn"):
            attrs["probe_sn"] = row["probe_sn"]
        return attrs
