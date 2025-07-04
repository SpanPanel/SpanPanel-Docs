# Home Assistant Synthetic Sensors Integration Requirements

## Overview

The synthetic sensors package enables the HA Integration to create calculated sensors that appear as native entities under the SPAN HA Integration's devices.
The system uses Home Assistant's local storage for configuration persistence and implements automatic entity rename synchronization.

## Configuration Schema Authority

**Schema Relationship**:

- **YAML Schema**: Authoritative definition for all configuration of integration sensors or as adapted for user extensions
- **JSON Schema**: Derived directly from YAML schema for internal storage
- **Schema Evolution**: Changes to storage definitions start with YAML updates
- **Derivation Principle**: JSON structure always reflects YAML data but may be restructured for storage optimizations
- **Contract Source**: YAML defines the interface contract between integration and package
- **Mapping**: One-to-one bidirectional transformation without data loss

## Architecture Components

1. **SPAN HA Integration**: Manages devices, creates initial YAML synthetic sensor definitions, and native panel sensors
2. **Synthetic Sensors Package**: Creates and manages calculated synthetic sensors based on YAML definitions
3. **Local Storage**: JSON-based configuration persistence in HA storage managed by the package StorageManager
4. **YAML Services**: Import/export interface for user configuration management

## YAML Field Usage

The following YAML snippet illustrates the distinction between `entity_id` and `device_identifier`:

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

- **`device_identifier`**  Raw device identifier for registry lookup to determine device_id prefix in entity_id (`nj-2316-005k6`), associates sensor with device
- **`entity_id`**  Fully qualified device identifier with device name prefix in other contexts (can be modified by user)

**Entity ID Behavior**:

- **Integration-generated sensors**: Integration provides explicit `entity_id` with `device_identifier` for proper device association
- **User-defined (custom) sensors**: `entity_id` may be omitted and will be generated using standard HA mechanisms from the `name` field
- **Device association for user sensors**: `device_identifier` is optional in user-defined YAML; if provided, sensor associates with device, otherwise no device association
- **When `entity_id` is provided**: Package uses the explicit entity_id as-is, no validation against device prefix patterns
- **When `entity_id` is omitted**: Package generates entity_id using standard HA slugify mechanisms from device_name and sensor name
- **When both `entity_id` and `name` are omitted**: Package generates entity_id using standard HA slugify mechanisms from unique_id
- **Existing entity handling**: If entity with specified `entity_id` already exists, HA updates the existing entity (standard HA behavior)
- **Entity Collision**: HA automatically resolves entity_id conflicts by adding qualifier suffixes like '_2', '_3', etc. when registering duplicate entity_ids
- **No validation enforcement**: Package trusts explicit entity_id values completely, allowing maximum integration flexibility

## Integration Workflow

The integration workflow requirements are:

- Configure logging and initialize API client for ha-synthetic-sensors logging and SPAN Panel API connection
- Register device in device registry with proper `device_identifier` before synthetic sensor creation
- Create native HA sensors (panel sensors, unmapped circuits, and hardware status sensors that synthetics will depend on)
- Add native entities to HA by calling `async_add_entities()` to register native sensors in Home Assistant
- Create YAML configuration with synthetic sensor definitions, proper entity_ids and device associations
- Register backing entity IDs with synthetic package for virtual entities the integration can provide data for
- Create data provider callback to supply live data from SPAN API to synthetic sensors
- Configure synthetic package with domain integration and data provider callback
- Load synthetic package with YAML configuration passed directly to package
- Register synthetic sensors with HA through package interface

**Storage Integration (v1.2.0)**:

- Implement package storage manager with HA storage-based configuration management with YAML interface
- Migrate from v1.0 to v1.2.0 by converting existing configurations through generating YAML from installed configuration and creating storage
- Enable storage-based CRUD operations supporting add/update/delete operations through YAML-based storage interface

### Initial Configuration Creation

**Requirement**: Integration creates initial YAML configuration.

**Responsibilities**:

- Create unique storage key for the integration and synthetic package use
- Create initial sensor definitions through StorageManager Interface
- Initialize storage with default synthetic sensor definitions
- Make additions/changes to sensor definitions as necessary during the life cycle via the package manager
- Initiate the necessary reloads of the integration

**Interface Contract**:

- **YAML**: Direct mapping from existing YAML configuration schema with configuration sensor_set_id
- **Multiple Configurations**: Integration can create multiple configurations (integration defaults, integration optional, user custom, etc.)

### Configuration Organization and Storage

**Package-Owned Storage Management**:

- Integration provides declarative sensor definitions, package determines optimal storage structure
- Integration creates configuration sensor_set_id and sensor definitions, delegates storage activity to package
- Package owns and manages all storage complexity including normalization and entity reference management
- Package exposes a bulk interface for taking integration initial yaml definitions or other imports
- Package storage manager provides CRUD methods for complete sensors
- Integration CRUD pattern to modify a single sensor is to read the full sensor (with attributes), modify, and write
- Package listens for entity_id changes on the HA event bus and renames any entity_ids in the storage, flushes relevant cache, etc.

**Storage Management Interface**:

```python
# Integration delegates storage to package
storage_manager = await package.create_storage_manager(
    integration_domain="span_panel",
    storage_context=hass.storage_context
)

# Integration provides high-level configuration
await storage_manager.create_sensor_configuration(
    sensor_set_id="span_sensors",
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
    await self.storage_manager.create_sensor_configuration(sensor_set_id, name, sensors)
```

### Device Association

**Device and Entity Management**:

- Package associates sensors with devices using `device_identifier` regardless of entity_id format
- Integration controls initial entity_id definitions completely during bulk load
- Package uses `device_identifier` for device registry lookup independent of entity_id naming

**External Entity References**:

- Formula and variable references to external entities do not require device association
- HA enforces entity_id uniqueness automatically with suffix patterns (`_2`, `_3`, etc.)
- Integration and user are responsible for proper entity_ids to avoid collisions

**Package CRUD Behavior**:

- Accept explicit `entity_id` exactly as provided by integration during bulk loading
- Assume integration has validated data when using CRUD operations for sensor modifications
- Treat attempts to remove or modify non-existent sensors as error conditions
- Validate that newly created individual sensors are created by HA without entity_id modification
- Raise exception if HA modifies entity_id during individual sensor creation

### YAML Import/Export with Multiple Configurations

**Single Configuration Operations**:

- Integration specifies target configuration using sensor_set_id parameter
- YAML export/import operates on single sensor_set_id configuration per service call
- YAML content returned directly from export method invocation
- Integration specifies which configurations to export/import for user-defined sensor sets by sensor_set_id
- Import of user defined sensors overwrites any existing sensors of that sensor set
- Upon importing a sensor set already defined in storage the package will remove top level sensors that are not in the new
  set (excluding references in formulas and variables that are not top level sensors keys)
- The integration may request, and the package will provide, YAML export of any sensor set

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
- Import validates YAML structure and converts to storage format, invalid YAML for any sensor is an error condition for the entire set
- Export denormalizes internal storage back to user-friendly YAML format
- Bidirectional conversion maintains configuration integrity

## Implementation Requirements

### Integration Domain and Device Management

**SPAN HA Integration Requirements**:

- Pass integration domain to package during setup
- Create YAML configurations with device_identifier fields
- Use current formula/variable structure (direct entity_id references or variable references)
- Maintain current YAML structure

**Device Prefix Resolution**:

- Package queries device registry using `(integration_domain, device_identifier)` tuple
- Package uses standard slugification of `device.name` for entity_id prefix generation
- Integration registers devices with appropriate `device.name` for desired prefix
- Device prefix follows standard HA slugification rules
- No custom device prefix logic required in package

**Prefix Resolution Workflow**:

1. **Initial sensor creation**: Package looks up device using device_identifier
2. **Prefix generation**: `slugify(device.name)` to create entity_id prefix  
3. **Entity ID creation**: `sensor.{slugified_device_name}_{sensor_key}`
4. **Subsequent operations**: Package uses entity registry for current entity_ids

**Example**:

- Device registered with name: "Span Panel"
- Device prefix: `span_panel` (from slugification)
- Synthetic sensor: `sensor.span_panel_solar_total`

### Configuration Schema Example

```yaml
# Integration provides this structure to package
version: '1.0'
sensors:
  span_nj_2316_005k6_solar_inverter_instant_power:
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

### Storage and Entity Management

**Storage Structure**:

- Package stores entity_ids directly in sensor configurations as they appear in YAML
- Direct one-to-one mapping from YAML structure to JSON storage
- Package validates all entity references exist during configuration loading

**Entity Rename Handling**:

- Package listens for entity registry events and updates storage when entity_ids change
- Formula cache is cleared when entity references change due to renames
- Integration backing store references are updated automatically when entity_ids change in storage

**Responsibilities**:

**Integration**:

- Generate unique sensor_set_id for each configuration
- Provide migration from existing configurations by generating YAML for package consumption
- Provide sensor definitions with entity_ids in variables/formulas
- Utilize configuration operations (create, update, remove) through package interface
- Handle device lifecycle and notify package of device-related changes

**Package**:

- Accept declarative sensor definitions from integration in YAML form and store as JSON
- Implement entity registry event listener to detect entity_id changes
- Update storage automatically when entity_ids change in registry
- Manage storage structure and optimization internally
- Provide configuration management interface to integration
- Clear formula cache and update dependency tracking when configurations change

**Storage Manager Requirements**:

- Monitor entity registry events for entity_id changes
- Update stored configurations when entities are renamed
- Query registry by unique_id before creating new entity_ids
- HA storage operations with YAML interface for sensor management
- Migration from v1.0 to v1.2.0 by converting existing configurations to storage format

### Multiple Configuration Lifecycle

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

- Integration generates unique sensor_set_ids and manages configuration lifecycle
- Package handles storage and entity management for each configuration independently
- No coordination required between multiple configurations at package level

### Configuration Extension Interface

**Sensor Set ID and YAML Interface**:

- Each sensor set is identified by a unique string sensor_set_id (e.g., "span_sensors", "solar_synthetic_sensors")
- The integration passes the sensor_set_id and the YAML content directly to the package/storage manager for all operations
- There is no requirement for a package normalized UUID or for the sensor_set_id to be embedded in the YAML file; the sensor_set_id is defined by the integration
- The YAML content is the authoritative definition for the sensor set and is passed in-memory for bulk loading, import, or export

**Bulk and Targeted Operations**:

- **Bulk load:** The integration calls the storage manager with the sensor_set_id and the full YAML content to load or replace a sensor set
- **Add/Update/Delete:** The integration calls the storage manager with the sensor_set_id and the sensor key to add, update, or remove a single sensor within the set
- The package/storage manager maintains the mapping of sensor_set_id to sensor set in storage

**Configuration Management Interface**:

```python
# Bulk load or replace a sensor set
await storage_manager.create_sensor_configuration(sensor_set_id, yaml_contents)

# Add/update/delete a sensor within a set
await storage_manager.add_sensor(sensor_set_id, sensor_key, sensor_definition)
await storage_manager.update_sensor(sensor_set_id, sensor_key, updated_definition)
await storage_manager.remove_sensor(sensor_set_id, sensor_key)
await storage_manager.remove_sensor_set(sensor_set_id)
```

**Integration/Synthetic Package Interface**:

- **YAML-centric**: YAML is the authoritative interface for configuration, import/export, and bulk operations.
- **Atomic operations**: Storage update and sensor management happen together.
- **Immediate validation**: Package can validate and reject invalid configurations at call time.
- **Simple workflow**: Integration always uses sensor_set_id + YAML for bulk, and sensor_set_id + key for targeted operations
- **Consistent state**: No possibility of storage/sensor state mismatch.

### Error Handling Granularity

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

### Integration/Package Storage Relationship (v1.2.0)

**YAML-First Interface**:

- The integration's interface to the synthetic package is always YAML: the integration provides YAML sensor sets to the package for loading, and can request YAML sensor sets from the package for user editing or export
- No file-based YAML storage in v1.2.0 implementation - integration passes YAML directly to package in-memory
- The synthetic package manages JSON storage internally, using a handle to the Home Assistant storage system provided by the integration
- All configuration persistence (writes/reads) is handled by the package, but the integration always interacts with the package using YAML as the authoritative format

**Migration from v1.0 to v1.2.0**:

- v1.0 installations will be migrated by generating YAML from the existing installed entity configuration
- Generated YAML is passed to the package for initial v1.2.0 storage creation
- Post-migration, all changes use the v1.2.0 YAML-to-storage interface

**Design Benefits**:

- Integration can easily export, import, or present sensor sets to users in human-readable YAML format
- Package ensures atomic, validated storage and sensor lifecycle management
- Clear separation between user interface (YAML) and internal storage (JSON)
