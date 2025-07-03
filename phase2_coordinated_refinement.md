# Home Assistant Synthetic Sensors Integration Requirements

This document outlines the requireme### Initial Configuration Creation

**Requirement**: Integration creates initial YAML configuration with file-based storage.

**Current Implementation Status**: ✅ **FULLY IMPLEMENTED**
- SPAN integration generates YAML configurations
- Package loads sensors from YAML files
- Updates work through file-based operations
- Integration handles all YAML lifecycle management

**Responsibilities**:

- Create YAML sensor definitions with proper entity_ids and device associations
- Generate configuration files in HA config directories  
- Manage YAML updates through file operations (generate_config, update, remove)
- Initiate package reloads when YAML configuration changes

**Interface Contract**:

- **YAML**: Direct file-based YAML configuration that package loads
- **File Management**: Integration controls YAML file creation, updates, and deletion
- **Package Interaction**: Package loads configuration from YAML files provided by integration

**Missing Implementation** (Phase 4):

- Storage manager for HA native storage
- JSON-based configuration persistence
- Storage-based CRUD operations
- Migration from file-based to storage-based configurationing the `ha-synthetic-sensors` package with Home Assistant integrations, focusing on device-aware entity naming, local storage management, and runtime synchronization.

## Overview

The synthetic sensors package enables the HA Integration to create calculated sensors that appear as native entities under the SPAN HA Integration's devices.
The system uses Home Assistant's local storage for configuration persistence and implements automatic entity rename synchronization.

## Configuration Schema Authority

**Schema Relationship**:

- **YAML Schema**: Authoritative definition for all configuration of integration sensors or as adapted for user extensions
- **JSON Schema**: Derived directly from YAML schema for internal storage
- **Schema Evolution**: Changes to storage requirements start with YAML schema updates
- **Derivation Principle**: JSON structure always follows YAML structure exactly
- **Contract Source**: YAML defines the interface contract between integration and package
- **Mapping**: One-to-one bidirectional transformation without data loss

## Architecture Components

1. **SPAN HA Integration**: Manages devices, native sensors, and synthetic sensor definitions
2. **Synthetic Sensors Package**: Creates and manages calculated sensors, handles device prefix resolution
3. **Local Storage**: JSON-based configuration persistence in HA storage managed by the package StorageManager
4. **YAML Services**: Import/export interface for user configuration management

## YAML Field Usage

The following YAML snippet illustrates the distinction between `device_id` and `device_identifier`:

```yaml
sensors:
  span_nj-2316-005k6_circuit_0dad2f16cd514812ae1807b0457d473e_instantpowerw:
    name: Lights Dining Room Power
    entity_id: sensor.span_panel_circuit_2_power
    formula: source_value
    variables:
      source_value: span_panel_synthetic_backing.circuit_2_power
    unit_of_measurement: W
    device_class: power
    state_class: measurement
    device_identifier: nj-2316-005k6
```

**Device Key Distinctions**:

- **`device_identifier`**  Raw device identifier for registry lookup to determine deivce_id prefix in entity_id (`nj-2316-005k6`), associates sensor with device
- **`device_id`**  Fully qualified device identifier with device name prefix in other contexts (can be modified by user)

**Entity ID Behavior**:

- **When `entity_id` is provided**: Package uses the explicit entity_id as-is, no validation against device prefix patterns
- **When `entity_id` is omitted**: Package must look up device name from `device_identifier` and derive entity_id prefix (`sensor.{derived_prefix}_{sensor_key}`)
- **Existing entity handling**: If entity with specified `entity_id` already exists, HA updates the existing entity (standard HA behavior)
- **Entity Collision**: HA automatically resolves entity_id conflicts by adding qualifier suffixes like '_2', '_3', etc. when registering duplicate entity_ids
- **No validation enforcement**: Package trusts explicit entity_id values completely, allowing maximum integration flexibility

**Entity ID Inclusion Example**:

```yaml
sensors:
  solar_total:
    entity_id: sensor.custom_solar_total_power  # Package trusts this completely
    device_identifier: nj-2316-005k6
    formula: "phase_a + phase_b"
    variables:
      phase_a: sensor.span_panel_1_solar_a_power
      phase_b: sensor.span_panel_1_solar_b_power
    unit_of_measurement: W
```

## Integration Requirements

Based on the actual SPAN integration implementation, the correct order and requirements are:

**Configure logging and initialize API client** - Set up ha-synthetic-sensors logging and test SPAN Panel API connection
**Register device in device registry** - Ensure device exists with proper `device_identifier` before synthetic sensor creation
**Create native HA sensors** - Set up panel sensors, unmapped circuits, and hardware status sensors that synthetics will depend on
**Add native entities to HA** - Call `async_add_entities()` to register native sensors in Home Assistant
**Generate unified YAML configuration** - Create synthetic sensor definitions with proper entity_ids and device associations
**Register backing entity IDs** - Tell synthetic package which virtual entities the integration can provide data for
**Create data provider callback** - Set up function to supply live data from SPAN API to synthetic sensors
**Configure synthetic package** - Set up domain integration and data provider callback
**Load synthetic package with YAML** - Initialize synthetic sensors using generated file-based YAML configuration
 **Register synthetic sensors with HA** - Create and add synthetic sensor entities through package interface

Phase 4: Storage Integration (**NOT YET IMPLEMENTED**)
**Implement package storage manager** - Replace file-based YAML with HA storage-based configuration management
**Migrate YAML to storage** - Convert existing file-based configurations to storage-managed configurations
**Enable storage-based CRUD operations** - Support add/update/delete operations through storage interface

### Initial Configuration Creation

**Requirement**: Integration creates initial YAMNL configuration.

**Responsibilities**:

- Create unique storage key for the integration and synthetic package use
- Create initial sensor definitions through StorageManager Interface
- Initialize storage with default synthetic sensor definitions
- Make additions/changes to sensor definitions as necessary during the life cycle via the package manager
- Initiate the necessary reloads of the integration

**Interface Contract**:

- **YAML**: Direct mapping from existing YAML configuration schema with configuration sensor_set_id
- **Multiple Configurations**: Integration can create multiple configurations (integration defaults, user customs, etc.)

### Configuration Organization and Storage

**Package-Owned Storage Management**:

- Integration provides declarative sensor definitions, package determines optimal storage structure
- Integration creates configuration sensor_set_id and sensor definitions, delegates storage anctivity to package
- Package owns and manages all storage complexity including normalization and entity reference management
- Package stores and merges integration definitions in storage and cache
- Package storage manager provides CRUD methods for complete sensors and sensor attributes
- Package storage manager takes base bulk sensor YAML and merges existing sensors with additional sensor attributes already in storage
- Integrtation CRUD pattern to modify a single sensor is to read the full sensor (with attributes), modify, and write
- Package handles entity_id reference normalization within formulas/variables to optimize for efficient rename operations
- Package listens for entity_id changes on the HA event bus and renames any entity_ids in the storage

**Storage Management Interface**:

```python
# Integration delegates storage to package
storage_manager = await package.create_storage_manager(
    integration_domain="span_panel",
    storage_context=hass.storage_context
)

# Integration provides high-level configuration
await storage_manager.create_configuration(
    config_uuid="uuid1",
    name="Integration Solar Defaults",
    sensors=sensor_definitions  # Package handles normalization
)
```

### Storage Manager Interface Lifecycle

**Integration Lifecycle Alignment**:

- Storage manager created once per integration instance during integration setup on new install
- Storage manager reused throughout integration lifecycle for all configuration operations
- Storage manager follows integration lifecycle: startup → running → shutdown → cleanup

**Storage Manager Creation**:

```python
# Integration setup - create storage manager once
async def async_setup_entry(hass, config_entry, async_add_entities):
    self.storage_manager = await package.create_storage_manager(
        integration_domain="span_panel",
        storage_context=hass.storage_context
    )
    
    # Use same manager for all configurations
    await self.storage_manager.create_configuration(config_uuid, name, sensors)
```

### Entity ID Override with Device Association

**Device Association Independence**:

- Package associates sensors with devices using `device_identifier` regardless of entity_id format
- No validation or enforcement of device prefix patterns in entity_id
- Integration controls entity_id completely, including legacy cases without device prefixes
- Package uses `device_identifier` for device registry lookup independent of entity_id naming

**External Entity References**:

- Formula and variable references to external entities do not require device association
- External entity references handled through normalization without device constraints
- HA enforces entity_id uniqueness automatically with suffix patterns (`_2`, `_3`, etc.)

**Entity ID Override Examples**:

```yaml
sensors:
  legacy_sensor:
    entity_id: sensor.solar_power  # No device prefix (legacy case)
    device_identifier: nj-2316-005k6  # Still associates with device
    formula: "external_temp + panel_adjustment"
    variables:
      external_temp: sensor.weather_station_temp  # External reference, no device association
      panel_adjustment: 5.0  # Literal value
```

**Package Behavior**:

- Use explicit `entity_id` exactly as provided by integration
- Associate sensor with device using `device_identifier` regardless of entity_id format
- Normalize external entity references without requiring device association
- No prefix pattern validation or enforcement

### YAML Import/Export with Multiple Configurations

**Single Configuration Operations**:

- YAML export/import operates on single configuration per service call
- Integration specifies target configuration using sensor_set_id parameter
- YAML content returned directly from export method invocation
- Integration controls which configurations to export/import for user-defined sensor sets
- Import of user defined sensors overwrites any existing sensors of that sensor set
- Integration may export sesnor definition of integration defined sensors for analysis

**YAML Service Interface**:

```python
# Export specific configuration to YAML
yaml_content = await storage_manager.export_yaml(sensor_set_id="span_sensors")

# Import YAML to specific configuration
await storage_manager.import_yaml(sensor_set_id="span_sensors", yaml_content=yaml_string)

# Integration manages multiple configurations as needed
for sensor_set_id in self.managed_configurations:
    if user_requests_export(sensor_set_id):
        yaml_content = await self.storage_manager.export_yaml(sensor_set_id)
        save_user_file(f"{sensor_set_id}.yaml", yaml_content)
```

**YAML Structure Consistency**:

- Exported YAML matches configuration schema used for integration definitions including all attributes
- Import validates YAML structure and converts to normalized storage format, invalid YAML is an error condition for the entire set
- Export denormalizes internal storage back to user-friendly YAML format
- Bidirectional conversion maintains configuration integrity

## Phased Implementation Strategy

### Phase 1: Domain Integration and Device Prefix Resolution

**Objective**: Establish foundational domain passing and proper entity_id generation from device prefixes.

**SPAN HA Integration Phase 1 Requirements**:

- **Pass integration domain to package during setup** - Integration explicitly provides its domain as a parameter during package initialization
- Generate YAML configurations with device_identifier fields
- **Use current formula/variable structure** - Formulas and variables may contain either direct entity_id references (e.g., `sensor.span_panel_1_solar_power`) or variable references (e.g., `solar_power` defined in variables section)
- **Maintain current YAML structure** - Existing YAML configuration format is sufficient for Phase 1 needs and requires no changes

**Synthetic Sensors Package Phase 1 Requirements**:

- **Accept integration_domain parameter during setup** - Package receives and stores the integration domain explicitly passed by the integration at startup
- Process YAML to create sensors with proper entity_ids:
  - Look up device using `(integration_domain, device_identifier)` tuple
  - Slugify `device.name` to generate device prefix
  - Create entity_id as `sensor.{slugified_device_name}_{sensor_key}`
  - Support explicit entity_id overrides from YAML
- **Handle mixed entity reference formats** - Support both direct entity_id references and variable-based references in formulas as they currently exist
- Create synthetic sensors with correct device association

**Phase 1 Validation**:

- Verify device association in HA device registry
- Confirm entity_id patterns match device naming
- Test with both derived and explicit entity_ids
- Validate cross-device configurations work properly

**Configuration Schema for Integration**:

```yaml
# Integration provides this structure to package per the validation schema
version: '1.0'
sensors:
  solar_inverter_instant_power:
    name: Solar Inverter Instant Power
    entity_id: sensor.span_panel_solar_inverter_instant_power
    formula: leg1_power + leg2_power
    variables:
      leg1_power: sensor.span_panel_unmapped_tab_30_power
      leg2_power: sensor.span_panel_unmapped_tab_32_power
    unit_of_measurement: W
    device_class: power
    state_class: measurement
    device_identifier: nj-2316-005k6
```

**Storage Structure Requirements**:

- **Direct Entity Storage** - package stores entity_ids directly in sensor configurations as they appear in YAML
- **Simple JSON Mapping** - direct one-to-one mapping from YAML structure to JSON storage
- **Entity Rename Handling** - when entity renames occur, update configurations by scanning and replacing entity_ids (acceptable for small datasets)
- **Validation** - package validates all entity references exist during configuration loading

**Storage Structure Example**:

```json
{
  "config_id": "sensor_set_id", 
  "name": "Solar Defaults",
  "sensors": {
    "solar_efficiency": {
      "formula": "solar_power / weather_temp",
      "variables": {
        "solar_power": "sensor.span_panel_1_solar_power",
        "weather_temp": "sensor.weather1.ambient_temp"
      }
    }
  }
}
```

**Entity Rename Handling**:

- **No automatic monitoring**: Package does not currently monitor entity registry events for entity renames
- **Manual update required**: Entity renames require manual intervention to update synthetic sensor configurations
- **Configuration update triggers**: When configurations are updated with new entity_ids, the package clears formula cache and updates dependency tracking
- **Simple implementation**: Direct storage scanning and replacement is appropriate for small datasets when manual updates occur

**Current Package Behavior**:
- Formula cache is cleared when sensor configurations are updated (`evaluator.clear_cache()`)
- Dependency listeners are updated when entity references change in formulas
- No automatic entity_id migration - requires integration or user intervention

**Integration Responsibilities**:

- Generate unique config_id (sensor_set_id) for each configuration
- Provide sensor definitions with entity_ids in variables/formulas
- Request configuration operations (create, update, remove) through package interface
- Handle device lifecycle and notify package of device-related changes

**Package Responsibilities**:

- Accept declarative sensor definitions from integration
- Store entity_ids directly in sensor configurations as they appear in YAML
- Manage storage structure and optimization internally  
- Provide configuration management interface to integration
- Clear formula cache and update dependency tracking when configurations change

### Device Prefix Resolution Method

**Standard Slugification Approach**:

- Package queries device registry using `(integration_domain, device_identifier)` tuple
- Package uses standard slugification of `device.name` for entity_id prefix generation
- No custom naming patterns or user-based device naming supported
- Device names controlled entirely by integration during device registration

**Prefix Resolution Workflow**:

1. **Initial sensor creation**: Package looks up device using device_identifier
2. **Prefix generation**: `slugify(device.name)` to create entity_id prefix
3. **Entity ID creation**: `sensor.{slugified_device_name}_{sensor_key}`
4. **Subsequent operations**: Package uses entity registry for current entity_ids

**Integration Device Naming Requirements**o:

- Integration registers devices with appropriate `device.name` for desired prefix
- Device prefix follows standard HA slugification rules
- No custom device prefix logic required in package
- Legacy installations with missing device prefixes supported but not created new

**Example**:

- Device registered with name: "Span Panel"
- Device prefix: `span_panel` (from slugification)
- Synthetic sensor: `sensor.span_panel_solar_total`

### 3. Multiple Configuration Lifecycle

**Entity ID Conflict Prevention**:

- Integration will not allow sensor key conflicts within its own domain
- Each synthetic sensor definition references unique entity_ids within the integration's scope
- Integration responsibility to ensure no duplicate sensor keys for same device across multiple configurations

**Home Assistant Entity ID Resolution**:

- If entity_id conflicts occur despite integration controls, HA automatically resolves with suffixes (`_2`, `_3`, etc.)
- Package relies on HA's built-in conflict resolution mechanism
- No special conflict handling required in package - HA handles gracefully

**Multiple Configuration Behavior**:

- Each configuration (sensor_set_id) operates independently, creating distinct sets of sensors
- Sensors from different configurations appear as separate entities in HA
- No merging of sensors across configurations - each maintains distinct identity
- Package may manage multiple configurations simultaneously for same integration

**Cross-Domain Entity References**:

- Synthetic formulas may reference entities from other domains (e.g., weather sensors)
- Entity_id uniqueness enforced globally by HA across all domains
- Package normalizes all entity references regardless of source domain
- Integration provides complete entity_ids, package handles normalization uniformly

**Configuration Coordination**:

- Integration generates unique config sensor_set_id's and manages configuration lifecycle
- Package handles storage and entity management for each configuration independently
- No coordination required between multiple configurations at package level

### onfiguration Extension Interface

**Sensor Set ID and YAML Interface**:

- Each sensor set is identified by a unique string set_id (e.g., "span_sensors", "solar_synthetic_sensors").
- The integration passes the set_id and the YAML content directly to the package/storage manager for all operations.
- There is no requirement for a package normalized UUID or for the set_id to be embedded in the YAML file; the set_id is defined by the integration
- The YAML content is the authoritative definition for the sensor set and is passed in-memory for bulk loading, import, or export.

**Bulk and Targeted Operations**:

- **Bulk load:** The integration calls the storage manager with the set_id and the full YAML content to load or replace a sensor set.
- **Add/Update/Delete:** The integration calls the storage manager with the set_id and the sensor key to add, update, or remove a single sensor within the set.
- The package/storage manager maintains the mapping of set_id to sensor set in storage

**Configuration Management Interface**:

```python
# Bulk load or replace a sensor set
await storage_manager.load_sensor_set(set_id, yaml_contents)

# Add/update/delete a sensor within a set
await storage_manager.add_sensor(set_id, sensor_key, sensor_definition)
await storage_manager.update_sensor(set_id, sensor_key, updated_definition)
await storage_manager.remove_sensor(set_id, sensor_key)
await storage_manager.remove_sensor_set(set_id)
```

**Integration/Symthethetic Package Interface**:

- **YAML-centric**: YAML is the authoritative interface for configuration, import/export, and bulk operations.
- **Atomic operations**: Storage update and sensor management happen together.
- **Immediate validation**: Package can validate and reject invalid configurations at call time.
- **Simple workflow**: Integration always uses set_id + YAML for bulk, and set_id + key for targeted operations.
- **Consistent state**: No possibility of storage/sensor state mismatch.

### 7. Error Handling Granularity

**Device Lifecycle Error Handling**:

- **SPAN HA Integration owns device lifecycle** - responsible for detecting device removal/addition via device registry events
- **Device removal flow**: SPAN HA Integration updates storage → removes affected sensors → notifies package
- **Package sensor failures** - throw exceptions for individual sensors, continue with others
- **SPAN HA Integration responsibility** - resolve device issues and update storage accordingly

**Runtime Error Behavior**:

```python
# Package sensor update behavior
try:
    await update_sensor(sensor_key, device_identifier)
except DeviceNotFoundError as e:
    logger.error(f"Device {device_identifier} not found for sensor {sensor_key}")
    # Continue with other sensors - SPAN HA Integration will fix eventually
    
except ConfigurationError as e:
    logger.error(f"Configuration error for sensor {sensor_key}: {e}")
    # Continue with other sensors
```

**Error Handling Principles**:

- **Individual sensor failures** - don't fail entire configuration
- **Exception propagation** - package throws exceptions for device/configuration issues
- **SPAN HA Integration resolution** - SPAN HA Integration expected to monitor and resolve device lifecycle issues
- **Temporary failures acceptable** - package continues operation, SPAN HA Integration fixes underlying issues
- **Clear error logging** - detailed error messages for troubleshooting

**Device Removal Scenario**:

1. SPAN HA Integration detects device removal via device registry events
2. SPAN HA Integration updates storage to remove sensors associated with removed device
3. SPAN HA Integration notifies package of removed sensor keys
4. Package cleanly removes synthetic sensors for removed device

### Integration/Package Storage Relationship

- The integration's interface to the synthetic package is always YAML: the integration provides YAML sensor sets to the package for loading,
  and can request YAML sensor sets from the package for user editing or export.
- The synthetic package manages JSON storage internally, using a handle to the Home Assistant storage system provided by the integration.
- All configuration persistence (writes/reads) is handled by the package, but the integration always interacts with the package using YAML as the authoritative format.
- This design allows the integration to easily export, import, or present sensor sets to the user in a human-readable format, while the package ensures atomic, validated storage and sensor lifecycle management.