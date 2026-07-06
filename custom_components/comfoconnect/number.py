"""Number entities for the ComfoConnect integration."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Callable

from aiocomfoconnect.const import (
    UNIT_TEMPHUMCONTROL,
    UNIT_VENTILATIONCONFIG,
    PdoType,
    VentilationSpeed,
)
from aiocomfoconnect.properties import (
    PROPERTY_CLIME_COOLING_COMFORT_TEMP,
    PROPERTY_CLIME_COOLING_KNEE_POINT,
    PROPERTY_CLIME_COOLING_TEMP_LIMIT,
    PROPERTY_CLIME_HEATING_COMFORT_TEMP,
    PROPERTY_CLIME_HEATING_DELTA,
    PROPERTY_CLIME_HEATING_KNEE_POINT,
    PROPERTY_CLIME_HEATPUMP_MAX_TEMP,
    PROPERTY_CLIME_HEATPUMP_MIN_TEMP,
    PROPERTY_CLIME_MANUAL_TARGET_TEMP,
    PROPERTY_RMOT_COOLING_THRESHOLD,
    PROPERTY_RMOT_HEATING_THRESHOLD,
    Property,
)
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, SIGNAL_COMFOCONNECT_AVAILABILITY, ComfoConnectBridge

_LOGGER = logging.getLogger(__name__)

PROPERTY_RANGE = 0x20
PROPERTY_STEP = 0x40


@dataclass
class ComfoConnectNumberEntityDescription(NumberEntityDescription):
    """Describes a ComfoConnect number entity."""

    unit: int | None = None
    subunit: int | None = None
    property_id: int | None = None
    property_type: int | None = None
    scale: int = 1
    speed: str | None = None
    get_value_fn: Callable[[ComfoConnectBridge], Awaitable[Any]] | None = None
    set_value_fn: Callable[[ComfoConnectBridge, float], Awaitable[Any]] | None = None


def _comfoclime_temperature_getter(prop: Property) -> Callable[[ComfoConnectBridge], Awaitable[Any]]:
    """Build a getter for a ComfoClime temperature, stored in tenths of a degree."""

    async def get_value(ccb: ComfoConnectBridge) -> float:
        return await ccb.get_comfoclime_property(prop) / 10

    return get_value


def _comfoclime_temperature_setter(prop: Property) -> Callable[[ComfoConnectBridge, float], Awaitable[Any]]:
    """Build a setter for a ComfoClime temperature, stored in tenths of a degree."""

    async def set_value(ccb: ComfoConnectBridge, value: float) -> None:
        await ccb.set_comfoclime_property(prop, round(value * 10))

    return set_value


def _temperature_getter(prop: Property) -> Callable[[ComfoConnectBridge], Awaitable[Any]]:
    """Build a getter for a ventilation unit temperature, stored in tenths of a degree."""

    async def get_value(ccb: ComfoConnectBridge) -> float:
        return await ccb.get_property(prop) / 10

    return get_value


def _temperature_setter(prop: Property) -> Callable[[ComfoConnectBridge, float], Awaitable[Any]]:
    """Build a setter for a ventilation unit temperature, stored in tenths of a degree."""

    async def set_value(ccb: ComfoConnectBridge, value: float) -> None:
        await ccb.set_property_typed(prop.unit, prop.subunit, prop.property_id, round(value * 10), prop.property_type)

    return set_value


COMFOCLIME_NUMBER_TYPES = (
    ComfoConnectNumberEntityDescription(
        key="comfoclime_heating_comfort_temperature",
        name="Heating comfort temperature",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=15,
        native_max_value=25,
        native_step=0.5,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_HEATING_COMFORT_TEMP),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_HEATING_COMFORT_TEMP),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_cooling_comfort_temperature",
        name="Cooling comfort temperature",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=28,
        native_step=0.5,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_COOLING_COMFORT_TEMP),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_COOLING_COMFORT_TEMP),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_manual_target_temperature",
        name="Manual target temperature",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=18,
        native_max_value=28,
        native_step=0.5,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_MANUAL_TARGET_TEMP),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_MANUAL_TARGET_TEMP),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_heating_knee_point",
        name="Heating knee point",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=15,
        native_step=0.5,
        entity_registry_enabled_default=False,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_HEATING_KNEE_POINT),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_HEATING_KNEE_POINT),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_cooling_knee_point",
        name="Cooling knee point",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=15,
        native_max_value=25,
        native_step=0.5,
        entity_registry_enabled_default=False,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_COOLING_KNEE_POINT),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_COOLING_KNEE_POINT),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_cooling_temperature_limit",
        name="Cooling temperature limit",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=28,
        native_step=0.5,
        entity_registry_enabled_default=False,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_COOLING_TEMP_LIMIT),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_COOLING_TEMP_LIMIT),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_heating_reduction_delta",
        name="Heating reduction delta",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=5,
        native_step=0.5,
        entity_registry_enabled_default=False,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_HEATING_DELTA),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_HEATING_DELTA),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_heatpump_min_temperature",
        name="Heat pump minimum temperature",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=17,
        native_step=1,
        entity_registry_enabled_default=False,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_HEATPUMP_MIN_TEMP),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_HEATPUMP_MIN_TEMP),
    ),
    ComfoConnectNumberEntityDescription(
        key="comfoclime_heatpump_max_temperature",
        name="Heat pump maximum temperature",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=40,
        native_max_value=60,
        native_step=1,
        entity_registry_enabled_default=False,
        get_value_fn=_comfoclime_temperature_getter(PROPERTY_CLIME_HEATPUMP_MAX_TEMP),
        set_value_fn=_comfoclime_temperature_setter(PROPERTY_CLIME_HEATPUMP_MAX_TEMP),
    ),
)

COMFOCLIME_UNIT_NUMBER_TYPES = (
    ComfoConnectNumberEntityDescription(
        key="rmot_heating_threshold",
        name="RMOT heating threshold",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=20,
        native_step=0.5,
        entity_registry_enabled_default=False,
        get_value_fn=_temperature_getter(PROPERTY_RMOT_HEATING_THRESHOLD),
        set_value_fn=_temperature_setter(PROPERTY_RMOT_HEATING_THRESHOLD),
    ),
    ComfoConnectNumberEntityDescription(
        key="rmot_cooling_threshold",
        name="RMOT cooling threshold",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=35,
        native_step=0.5,
        entity_registry_enabled_default=False,
        get_value_fn=_temperature_getter(PROPERTY_RMOT_COOLING_THRESHOLD),
        set_value_fn=_temperature_setter(PROPERTY_RMOT_COOLING_THRESHOLD),
    ),
)

NUMBER_TYPES = (
    ComfoConnectNumberEntityDescription(
        key="airflow_away",
        name="Away airflow target",
        icon="mdi:fan-speed-1",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.BOX,
        unit=UNIT_VENTILATIONCONFIG,
        subunit=1,
        property_id=3,
        property_type=PdoType.TYPE_CN_INT16,
        speed=VentilationSpeed.AWAY,
    ),
    ComfoConnectNumberEntityDescription(
        key="airflow_low",
        name="Low airflow target",
        icon="mdi:fan-speed-1",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.BOX,
        unit=UNIT_VENTILATIONCONFIG,
        subunit=1,
        property_id=4,
        property_type=PdoType.TYPE_CN_INT16,
        speed=VentilationSpeed.LOW,
    ),
    ComfoConnectNumberEntityDescription(
        key="airflow_medium",
        name="Medium airflow target",
        icon="mdi:fan-speed-2",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.BOX,
        unit=UNIT_VENTILATIONCONFIG,
        subunit=1,
        property_id=5,
        property_type=PdoType.TYPE_CN_INT16,
        speed=VentilationSpeed.MEDIUM,
    ),
    ComfoConnectNumberEntityDescription(
        key="airflow_high",
        name="High airflow target",
        icon="mdi:fan-speed-3",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.BOX,
        unit=UNIT_VENTILATIONCONFIG,
        subunit=1,
        property_id=6,
        property_type=PdoType.TYPE_CN_INT16,
        speed=VentilationSpeed.HIGH,
    ),
    ComfoConnectNumberEntityDescription(
        key="rmot_heating",
        name="Heating RMOT threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        unit=UNIT_TEMPHUMCONTROL,
        subunit=1,
        property_id=2,
        property_type=PdoType.TYPE_CN_INT16,
        scale=10,
    ),
    ComfoConnectNumberEntityDescription(
        key="rmot_cooling",
        name="Cooling RMOT threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        unit=UNIT_TEMPHUMCONTROL,
        subunit=1,
        property_id=3,
        property_type=PdoType.TYPE_CN_INT16,
        scale=10,
    ),
    ComfoConnectNumberEntityDescription(
        key="temperature_profile_warm",
        name="Warm profile target temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        unit=UNIT_TEMPHUMCONTROL,
        subunit=1,
        property_id=10,
        property_type=PdoType.TYPE_CN_INT16,
        scale=10,
    ),
    ComfoConnectNumberEntityDescription(
        key="temperature_profile_normal",
        name="Normal profile target temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        unit=UNIT_TEMPHUMCONTROL,
        subunit=1,
        property_id=11,
        property_type=PdoType.TYPE_CN_INT16,
        scale=10,
    ),
    ComfoConnectNumberEntityDescription(
        key="temperature_profile_cool",
        name="Cool profile target temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        unit=UNIT_TEMPHUMCONTROL,
        subunit=1,
        property_id=12,
        property_type=PdoType.TYPE_CN_INT16,
        scale=10,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ComfoConnect number entities."""
    ccb = hass.data[DOMAIN][config_entry.entry_id]

    numbers: list[ComfoConnectNumber] = []
    if ccb.comfoclime_serial:
        numbers.extend(
            ComfoConnectNumber(ccb=ccb, description=description, device_id=ccb.comfoclime_serial)
            for description in COMFOCLIME_NUMBER_TYPES
        )
        numbers.extend(ComfoConnectNumber(ccb=ccb, description=description) for description in COMFOCLIME_UNIT_NUMBER_TYPES)

    numbers.extend(ComfoConnectNumber(ccb=ccb, description=description) for description in NUMBER_TYPES)
    async_add_entities(numbers, True)


class ComfoConnectNumber(NumberEntity):
    """Representation of a ComfoConnect number."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True
    _attr_should_poll = True
    entity_description: ComfoConnectNumberEntityDescription

    def __init__(
        self,
        ccb: ComfoConnectBridge,
        description: ComfoConnectNumberEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the ComfoConnect number."""
        self._ccb = ccb
        self.entity_description = description
        self._attr_unique_id = f"{self._ccb.uuid}-{description.key}"
        self._attr_available = ccb.is_available
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id or self._ccb.uuid)},
        )

    async def async_added_to_hass(self) -> None:
        """Register for availability changes."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_COMFOCONNECT_AVAILABILITY.format(self._ccb.uuid),
                self._handle_availability_update,
            )
        )

    @callback
    def _handle_availability_update(self, available: bool) -> None:
        """Handle bridge availability changes."""
        self._attr_available = available
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the value and constraints for this number."""
        if self.entity_description.get_value_fn is not None:
            self._attr_native_value = await self.entity_description.get_value_fn(self._ccb)
            return

        self._attr_native_value = self._decode_value(
            await self._ccb.get_single_property(
                self.entity_description.unit,
                self.entity_description.subunit,
                self.entity_description.property_id,
                self.entity_description.property_type,
            )
        )
        await self._update_constraints()

    async def async_set_native_value(self, value: float) -> None:
        """Set the configured value."""
        if self.entity_description.set_value_fn is not None:
            await self.entity_description.set_value_fn(self._ccb, value)
            self._attr_native_value = value
            self.async_write_ha_state()
            return

        encoded_value = round(value * self.entity_description.scale)
        if self.entity_description.speed:
            await self._ccb.set_flow_for_speed(self.entity_description.speed, encoded_value)
        else:
            await self._ccb.set_property_typed(
                self.entity_description.unit,
                self.entity_description.subunit,
                self.entity_description.property_id,
                encoded_value,
                self.entity_description.property_type,
            )

        self._attr_native_value = value

    async def _update_constraints(self) -> None:
        """Read min, max, and step metadata from the ventilation unit."""
        if self.entity_description.unit is None or self.entity_description.subunit is None:
            return

        range_data = await self._read_property_metadata(PROPERTY_RANGE)
        if len(range_data) >= 2:
            self._attr_native_min_value = self._decode_value(range_data[0])
            self._attr_native_max_value = self._decode_value(range_data[1])

        step_data = await self._read_property_metadata(PROPERTY_STEP)
        if step_data:
            self._attr_native_step = self._decode_value(step_data[0])

    async def _read_property_metadata(self, kind: int) -> list[int]:
        """Read typed property metadata values from the bridge."""
        if self.entity_description.unit is None or self.entity_description.subunit is None:
            return []

        result = await self._ccb.cmd_rmi_request(
            bytes(
                [
                    0x01,
                    self.entity_description.unit,
                    self.entity_description.subunit,
                    kind,
                    self.entity_description.property_id,
                ]
            )
        )
        data = bytes(result.message)
        if len(data) % 2:
            return []
        return [int.from_bytes(data[index : index + 2], byteorder="little", signed=True) for index in range(0, len(data), 2)]

    def _decode_value(self, value: int) -> float:
        """Decode raw property values to their native Home Assistant value."""
        return value / self.entity_description.scale
