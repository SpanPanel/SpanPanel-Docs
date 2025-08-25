"""Solar synthetic sensor generation for SPAN Panel integration.

This module handles the generation of solar synthetic sensors using formula-based
calculations that reference native HA unmapped circuit entities.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.util import slugify

from .coordinator import SpanPanelCoordinator
from .helpers import (
    construct_120v_synthetic_entity_id,
    construct_240v_synthetic_entity_id,
    construct_synthetic_unique_id,
    construct_tabs_attribute,
    construct_voltage_attribute,
    get_unmapped_circuit_entity_id,
)
from .span_panel import SpanPanel
from .span_panel_circuit import SpanPanelCircuit
from .synthetic_utils import BackingEntity, combine_yaml_templates
from .util import panel_to_device_info

_LOGGER = logging.getLogger(__name__)

# Solar sensor definitions - these reference native HA entities via formulas
SOLAR_SENSOR_DEFINITIONS = [
    {
        "template": "solar_current_power.yaml.txt",
        "sensor_type": "power",
        "description": "Current solar power production",
    },
    {
        "template": "solar_produced_energy.yaml.txt",
        "sensor_type": "energy_produced",
        "description": "Total solar energy produced",
    },
    {
        "template": "solar_consumed_energy.yaml.txt",
        "sensor_type": "energy_consumed",
        "description": "Total solar energy consumed",
    },
]


def _extract_leg_numbers(leg1_circuit: str, leg2_circuit: str) -> tuple[int, int]:
    """Extract circuit numbers from leg circuit IDs.

    Args:
        leg1_circuit: Circuit ID for leg 1 (e.g., "unmapped_tab_15")
        leg2_circuit: Circuit ID for leg 2 (e.g., "unmapped_tab_16")

    Returns:
        Tuple of (leg1_number, leg2_number)

    """
    leg1_number = (
        int(leg1_circuit.replace("unmapped_tab_", ""))
        if leg1_circuit.startswith("unmapped_tab_")
        else 0
    )
    leg2_number = (
        int(leg2_circuit.replace("unmapped_tab_", ""))
        if leg2_circuit and leg2_circuit.startswith("unmapped_tab_")
        else 0
    )
    return leg1_number, leg2_number


def _get_leg_entities(
    span_panel: SpanPanel, leg1_number: int, leg2_number: int
) -> tuple[dict[str, str | int], list[str]]:
    """Generate entity IDs for leg circuits and collect required entities.

    This function first tries to find mapped circuits (regular circuits with UUIDs),
    then falls back to unmapped circuits if those don't exist.

    Args:
        span_panel: The SPAN Panel data
        leg1_number: Circuit number for leg 1
        leg2_number: Circuit number for leg 2

    Returns:
        Tuple of (leg_entities_dict, required_entities_list)

    """
    leg_entities = {}
    required_entities = []

    def _get_circuit_entity_id(tab_number: int, suffix: str) -> str | None:
        """Get entity ID for a circuit, trying mapped circuits first, then unmapped."""
        # First, try to find a mapped circuit that uses this tab number
        for circuit_id, circuit in span_panel.circuits.items():
            if hasattr(circuit, 'tabs') and circuit.tabs and tab_number in circuit.tabs:
                # This is a mapped circuit using this tab - construct its entity ID
                device_info = panel_to_device_info(span_panel)
                device_name_raw = device_info.get("name", "span_panel")
                device_name = slugify(device_name_raw) if device_name_raw else "span_panel"
                
                if len(circuit.tabs) == 1:
                    # Single tab circuit
                    entity_id = f"sensor.{device_name}_circuit_{tab_number}_{suffix}"
                    _LOGGER.debug("Found mapped single-tab circuit for tab %s: %s", tab_number, entity_id)
                    return entity_id
                else:
                    # Multi-tab circuit - use sorted tab numbers
                    sorted_tabs = sorted(circuit.tabs)
                    tabs_str = "_".join(str(t) for t in sorted_tabs)
                    entity_id = f"sensor.{device_name}_circuit_{tabs_str}_{suffix}"
                    _LOGGER.debug("Found mapped multi-tab circuit for tab %s: %s", tab_number, entity_id)
                    return entity_id
        
        # If no mapped circuit found, try unmapped circuit
        _LOGGER.debug("No mapped circuit found for tab %s, trying unmapped", tab_number)
        return get_unmapped_circuit_entity_id(span_panel, tab_number, suffix)

    # Generate entities for leg1
    if leg1_number > 0:
        _LOGGER.debug("Generating leg1 entities for tab number: %s", leg1_number)
        leg1_power_entity = _get_circuit_entity_id(leg1_number, "power")
        leg1_produced_entity = _get_circuit_entity_id(leg1_number, "energy_produced")
        leg1_consumed_entity = _get_circuit_entity_id(leg1_number, "energy_consumed")

        _LOGGER.debug("Leg1 entities: power=%s, produced=%s, consumed=%s", 
                     leg1_power_entity, leg1_produced_entity, leg1_consumed_entity)

        # Collect required entities and validate they exist
        for entity in [leg1_power_entity, leg1_produced_entity, leg1_consumed_entity]:
            if isinstance(entity, str):
                required_entities.append(entity)
        
        # If any leg1 entity is None, log error but don't use fallback numeric values
        if not all([leg1_power_entity, leg1_produced_entity, leg1_consumed_entity]):
            _LOGGER.error("Failed to generate some leg1 entity IDs for tab %s", leg1_number)
            _LOGGER.error("Generated: power=%s, produced=%s, consumed=%s", 
                         leg1_power_entity, leg1_produced_entity, leg1_consumed_entity)
    else:
        leg1_power_entity = leg1_produced_entity = leg1_consumed_entity = None

    # Generate entities for leg2
    if leg2_number > 0:
        _LOGGER.debug("Generating leg2 entities for tab number: %s", leg2_number)
        leg2_power_entity = _get_circuit_entity_id(leg2_number, "power")
        leg2_produced_entity = _get_circuit_entity_id(leg2_number, "energy_produced")
        leg2_consumed_entity = _get_circuit_entity_id(leg2_number, "energy_consumed")

        _LOGGER.debug("Leg2 entities: power=%s, produced=%s, consumed=%s", 
                     leg2_power_entity, leg2_produced_entity, leg2_consumed_entity)

        # Collect required entities and validate they exist
        for entity in [leg2_power_entity, leg2_produced_entity, leg2_consumed_entity]:
            if isinstance(entity, str):
                required_entities.append(entity)
                
        # If any leg2 entity is None, log error but don't use fallback numeric values
        if not all([leg2_power_entity, leg2_produced_entity, leg2_consumed_entity]):
            _LOGGER.error("Failed to generate some leg2 entity IDs for tab %s", leg2_number)
            _LOGGER.error("Generated: power=%s, produced=%s, consumed=%s", 
                         leg2_power_entity, leg2_produced_entity, leg2_consumed_entity)
    else:
        leg2_power_entity = leg2_produced_entity = leg2_consumed_entity = None

    leg_entities.update(
        {
            "leg1_power_entity": leg1_power_entity or "",
            "leg1_produced_entity": leg1_produced_entity or "",
            "leg1_consumed_entity": leg1_consumed_entity or "",
            "leg2_power_entity": leg2_power_entity or "",
            "leg2_produced_entity": leg2_produced_entity or "",
            "leg2_consumed_entity": leg2_consumed_entity or "",
        }
    )

    _LOGGER.debug("Final leg_entities dict: %s", leg_entities)
    _LOGGER.debug("Required entities list: %s", required_entities)

    return leg_entities, required_entities


def _get_template_attributes(leg1_number: int, leg2_number: int) -> tuple[str, int]:
    """Generate tabs and voltage attributes for solar sensors.

    Args:
        leg1_number: Circuit number for leg 1
        leg2_number: Circuit number for leg 2

    Returns:
        Tuple of (tabs_attribute, voltage_attribute)

    """
    if leg1_number > 0 and leg2_number > 0:
        # Create a synthetic circuit object with both tab numbers for attribute generation
        synthetic_circuit = SpanPanelCircuit(
            circuit_id="solar_synthetic",
            name="Solar Synthetic",
            relay_state="CLOSED",
            instant_power=0.0,
            instant_power_update_time=0,
            produced_energy=0.0,
            consumed_energy=0.0,
            energy_accum_update_time=0,
            priority="NORMAL",
            is_user_controllable=False,
            is_sheddable=False,
            is_never_backup=False,
            tabs=[leg1_number, leg2_number],
        )
        tabs_attribute_full = construct_tabs_attribute(synthetic_circuit)
        voltage_attribute = construct_voltage_attribute(synthetic_circuit)

        tabs_attribute = tabs_attribute_full if tabs_attribute_full else ""
        voltage_attribute = voltage_attribute if voltage_attribute is not None else 0
    else:
        tabs_attribute = ""
        voltage_attribute = 0

    return tabs_attribute, voltage_attribute


def _generate_sensor_entity_id(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    sensor_type: str,
    leg1_number: int,
    leg2_number: int,
) -> str | None:
    """Generate entity ID for a solar sensor.

    Args:
        coordinator: The SPAN Panel coordinator
        span_panel: The SPAN Panel data
        sensor_type: Type of sensor (e.g., "power", "energy_produced")
        leg1_number: Circuit number for leg 1
        leg2_number: Circuit number for leg 2

    Returns:
        Entity ID string or None if generation fails

    """
    if leg1_number > 0 and leg2_number > 0:
        # Two tabs - use 240V synthetic helper
        return construct_240v_synthetic_entity_id(
            coordinator,
            span_panel,
            "sensor",
            sensor_type,
            friendly_name="Solar",
            tab1=leg1_number,
            tab2=leg2_number,
            unique_id=None,
        )
    else:
        # Single tab - use 120V synthetic helper
        active_tab = leg1_number if leg1_number > 0 else leg2_number
        return construct_120v_synthetic_entity_id(
            coordinator,
            span_panel,
            "sensor",
            sensor_type,
            friendly_name="Solar",
            tab=active_tab,
            unique_id=None,
        )


async def _process_sensor_template(
    sensor_def: dict[str, Any],
    template_vars: dict[str, Any],
    entity_id: str | None,
) -> dict[str, Any] | None:
    """Process a sensor template and return the configuration.

    Args:
        sensor_def: Sensor definition dictionary
        template_vars: Template variables
        entity_id: Entity ID for the sensor

    Returns:
        Sensor configuration dictionary or None if processing fails

    """
    if not entity_id:
        return None

    # Validate that required entity variables are present and valid
    required_vars = []
    if "power" in sensor_def["sensor_type"]:
        required_vars = ["leg1_power_entity", "leg2_power_entity"]
    elif "produced" in sensor_def["sensor_type"]:
        required_vars = ["leg1_produced_entity", "leg2_produced_entity"]
    elif "consumed" in sensor_def["sensor_type"]:
        required_vars = ["leg1_consumed_entity", "leg2_consumed_entity"]
    
    # Check if any required variables are missing or empty
    for var in required_vars:
        if not template_vars.get(var) or template_vars[var] == "":
            _LOGGER.error(
                "Missing or empty required variable '%s' for sensor template %s. Variables: %s",
                var, sensor_def["template"], template_vars
            )
            return None

    # Add entity_id to template variables
    sensor_template_vars = template_vars.copy()
    sensor_template_vars["entity_id"] = entity_id

    # Convert template variables to strings, but preserve numeric attributes as unquoted
    string_template_vars = {}
    for key, value in sensor_template_vars.items():
        if key == "voltage_attribute" and isinstance(value, int | float):
            # Keep voltage as unquoted number for YAML
            string_template_vars[key] = str(value)
        elif isinstance(value, int | float):
            # Other numeric literals as strings  
            string_template_vars[key] = str(value)
        elif value is not None:
            string_template_vars[key] = str(value)
        else:
            string_template_vars[key] = ""

    _LOGGER.debug(
        "Solar template variables for %s: %r", sensor_def["template"], string_template_vars
    )

    try:
        template_files = [sensor_def["template"]]
        combined_result = await combine_yaml_templates(template_files, string_template_vars)
        _LOGGER.debug(
            "Template processing result for %s: %r", sensor_def["template"], combined_result
        )
    except Exception as template_error:
        _LOGGER.error(
            "Template processing failed for %s: %s",
            sensor_def["template"],
            template_error,
            exc_info=True,
        )
        return None

    if (
        not combined_result
        or not isinstance(combined_result, dict)
        or "sensor_configs" not in combined_result
    ):
        _LOGGER.error(
            "No sensors found in template %s. Combined result: %r",
            sensor_def["template"],
            combined_result,
        )
        return None

    # Extract the sensor configuration
    template_sensors = combined_result["sensor_configs"]
    if not template_sensors:
        _LOGGER.error(
            "Empty sensors in template %s. Template sensors: %r",
            sensor_def["template"],
            template_sensors,
        )
        return None

    # Get the first (and should be only) sensor from the template
    sensor_key = list(template_sensors.keys())[0]
    sensor_config = template_sensors[sensor_key].copy()

    _LOGGER.debug("Raw sensor config from template %s: %r", sensor_def["template"], sensor_config)

    # Create the final sensor configuration
    return {
        "entity_id": sensor_config.get("entity_id", entity_id),
        "name": sensor_config.get("name", ""),
        "formula": sensor_config.get("formula", ""),
        "variables": sensor_config.get("variables", {}),
        "attributes": sensor_config.get("attributes", {}),
        "metadata": sensor_config.get("metadata", {}),
    }


async def generate_solar_sensors(
    coordinator: SpanPanelCoordinator,
    span_panel: SpanPanel,
    leg1_circuit: str,
    leg2_circuit: str,
    device_name: str,
) -> tuple[dict[str, Any], list[BackingEntity], dict[str, Any]]:
    """Generate solar sensor configurations using YAML templates.

    Args:
        coordinator: The SPAN Panel coordinator
        span_panel: The SPAN Panel data
        leg1_circuit: Circuit ID for leg 1 (e.g., "unmapped_tab_15")
        leg2_circuit: Circuit ID for leg 2 (e.g., "unmapped_tab_16")
        device_name: The name of the device to use for sensor generation

    Returns:
        Tuple of (sensor_configs, backing_entities, global_settings)
        Note: backing_entities will be empty since solar uses formula references

    """
    sensor_configs = {}
    backing_entities: list[BackingEntity] = []  # Solar doesn't need backing entities

    # Get global settings from header template
    global_settings = {}
    try:
        # Get display precision from options
        power_precision = coordinator.config_entry.options.get("power_display_precision", 0)
        energy_precision = coordinator.config_entry.options.get("energy_display_precision", 2)

        # Provide device_identifier for template processing
        header_placeholders = {
            "device_identifier": span_panel.status.serial_number,
            "power_display_precision": str(power_precision),
            "energy_display_precision": str(energy_precision),
        }
        combined_result = await combine_yaml_templates([], header_placeholders)
        if (
            combined_result
            and isinstance(combined_result, dict)
            and "global_settings" in combined_result
            and combined_result["global_settings"] is not None
        ):
            global_settings = combined_result["global_settings"]
        _LOGGER.debug("Loaded global settings for solar sensors: %s", global_settings)
    except Exception as e:
        _LOGGER.warning("Could not load global settings for solar sensors: %s", e)

    # Extract circuit numbers from leg circuit IDs
    leg1_number, leg2_number = _extract_leg_numbers(leg1_circuit, leg2_circuit)

    # If no valid tabs are configured, don't generate any solar sensors
    if leg1_number == 0 and leg2_number == 0:
        _LOGGER.debug("No valid solar tabs configured, skipping solar sensor generation")
        return {}, [], global_settings

    # Generate entity IDs for leg circuits
    leg_entities, required_entities = _get_leg_entities(span_panel, leg1_number, leg2_number)

    # Verify that entity IDs were generated successfully for non-zero legs
    if not required_entities:
        _LOGGER.error(
            "No valid entities found for solar circuits %s and %s", leg1_circuit, leg2_circuit
        )
        return {}, [], global_settings
    
    # Verify all required entities are valid strings
    invalid_entities = [entity for entity in required_entities if not entity or not isinstance(entity, str)]
    if invalid_entities:
        _LOGGER.error(
            "Some entity IDs are invalid for solar circuits %s and %s: %s", 
            leg1_circuit, leg2_circuit, invalid_entities
        )
        return {}, [], global_settings

    # Get template attributes
    tabs_attribute, voltage_attribute = _get_template_attributes(leg1_number, leg2_number)

    # Template variables for solar sensors
    template_vars = {
        "device_identifier": span_panel.status.serial_number,
        "power_display_precision": str(
            coordinator.config_entry.options.get("power_display_precision", 0)
        ),
        "energy_display_precision": str(
            coordinator.config_entry.options.get("energy_display_precision", 2)
        ),
        "leg1_circuit": leg1_circuit,
        "leg2_circuit": leg2_circuit,
        "tabs_attribute": tabs_attribute,
        "voltage_attribute": str(voltage_attribute),
        **leg_entities,
    }

    _LOGGER.debug("Solar tabs_attribute value: %r", tabs_attribute)
    _LOGGER.debug("Solar tabs_attribute type: %s", type(tabs_attribute))
    _LOGGER.debug("Complete template_vars for solar sensors: %s", template_vars)

    # Generate each solar sensor
    for sensor_def in SOLAR_SENSOR_DEFINITIONS:
        try:
            # Generate entity ID for this sensor
            entity_id = _generate_sensor_entity_id(
                coordinator, span_panel, sensor_def["sensor_type"], leg1_number, leg2_number
            )

            unique_id = construct_synthetic_unique_id(
                span_panel.status.serial_number, f"solar_{sensor_def['sensor_type']}"
            )

            # Process the sensor template
            _LOGGER.debug("Processing template %s for sensor %s", sensor_def["template"], unique_id)
            final_config = await _process_sensor_template(sensor_def, template_vars, entity_id)
            if final_config:
                sensor_configs[unique_id] = final_config
                _LOGGER.debug("Successfully generated solar sensor: %s -> %s", unique_id, entity_id)
                _LOGGER.debug("Final config has formula: %s, variables: %s", 
                             bool(final_config.get("formula")), bool(final_config.get("variables")))
            else:
                _LOGGER.error("Template processing returned None for %s", sensor_def["template"])

        except Exception as e:
            _LOGGER.error(
                "Error generating solar sensor from template %s: %s", sensor_def["template"], e, exc_info=True
            )

    _LOGGER.debug("Generated %d solar sensor configurations", len(sensor_configs))
    return sensor_configs, backing_entities, global_settings


def get_solar_data_value(entity_part: str, span_panel: SpanPanel, sensor_map: dict) -> float:
    """Get solar data value - not used since solar uses formula references.

    This function exists for consistency with the pattern but solar sensors
    use formulas that reference native HA entities directly.
    """
    # Solar sensors don't use this pattern - they use formulas
    return 0.0