### Package Implementation Requirements

**Device Identifier Format**:
- Package expects `device_identifier` as a single string value (e.g., `"nj-2316-005k6"`)
- Package does NOT handle HA device identifier tuple format `(domain, identifier)`
- SPAN HA Integration must provide only the identifier portion, not the full tuple

**Device Registry Lookup**:
- Package searches for devices where `device_identifier` matches the identifier portion AND SPAN HA Integration domain matches
- SPAN HA Integration provides its domain during setup configuration, not in individual YAML sensor definitions
- Package looks for device with the specific identifier tuple: `(integration_domain, device_identifier)`
- Example: SPAN HA Integration domain `"span_panel"` + device_identifier `"nj-2316-005k6"` → searches for exact tuple `("span_panel", "nj-2316-005k6")`
- Package does NOT search across all identifier tuples in a device's identifier set

**Multiple Device Identifiers**:
- HA devices can have multiple identifier tuples: `[("span_panel", "id1"), ("mac_address", "id2"), ("model_serial", "id3")]`
- Package only matches against the SPAN HA Integration's own domain identifier tuple
- No ambiguity - package looks for exact `(integration_domain, device_identifier)` match
- Each SPAN HA Integration manages its own identifier namespace

**SPAN HA Integration Domain Scoping**:
- SPAN HA Integration passes domain once during package setup (e.g., `integration_domain="span_panel"`)
- Device identifiers can be non-unique across different SPAN HA Integration domains
- Package uses SPAN HA Integration domain + device_identifier for precise device lookup
- Prevents conflicts where multiple SPAN HA Integrations might use same identifier values

**Error Handling for Missing Devices**:
- **Missing device_identifier**: Raise configuration error, fail sensor creation
- **No matching device found**: Raise configuration error, fail sensor creation
- **No fallback behavior**: Package must not fall back to default prefixes or create orphaned sensors
- **Clear error messages**: Include device_identifier value and available devices in error reporting

### Device Management Authority and Timing

**Device Creation Authority**:
- **SPAN HA Integration creates devices first** - registers devices in HA device registry before synthetic sensor creation
- **Package never creates devices** - only associates synthetic sensors with existing devices
- **Strict dependency** - synthetic sensors cannot be created if target device does not exist
- **Clear separation** - SPAN HA Integration owns device lifecycle, package owns synthetic sensor lifecycle

**Device Association Requirements**:
- **Device identifier required** - all synthetic sensors must include device_identifier field in YAML
- **Device existence validation** - package checks if device with (integration_domain, device_identifier) exists
- **Device creation fallback** - if device does not exist, package can create it using additional YAML fields
- **Required fields for device creation**: device_name, device_manufacturer (minimum)
- **Optional fields for device creation**: device_model, device_sw_version, device_hw_version, suggested_area
- **Strict validation** - missing device_identifier or insufficient device creation fields results in configuration error

**Device Creation Fields**:
```yaml
sensors:
  sensor_key:
    device_identifier: "serial-123"     # Required: device association
    device_name: "My Device"            # Required: for device creation if needed
    device_manufacturer: "Acme Corp"    # Required: for device creation if needed
    device_model: "Model X"             # Optional: for device creation
    device_sw_version: "1.0.0"          # Optional: for device creation
    device_hw_version: "Rev A"          # Optional: for device creation
    suggested_area: "Living Room"       # Optional: for device creation
```

**Device Creation Behavior**:
- Package creates device only when device_identifier lookup fails
- Created device uses identifier tuple: (integration_domain, device_identifier)
- Device name derives entity_id prefix for synthetic sensors
- All synthetic sensors associate with the same created device if using same device_identifier
- **Logging requirement**: Package must log device creation at INFO level with device details (identifier, name, manufacturer)

**Prefix Resolution Timing**:
- **Entity creation time (dynamic)** - device name → prefix resolution happens when synthetic sensors are created/updated
- **Runtime updates** - prefix resolution updates when device names change (via entity rename events)
- **Not static** - configuration does not cache device name prefixes to ensure responsiveness to device renames
- **On-demand lookup** - package queries device registry each time prefix resolution is needed

**Device Name vs Entity ID Rename Coordination**:
- When user renames device in HA UI, HA prompts to rename associated entities
- If user chooses to rename entities: HA updates entity_ids automatically
- SPAN HA Integration responsibility: Detect entity_id changes via entity registry events and update stored YAML/JSON configuration
- SPAN HA Integration responsibility: Notify package of configuration changes after updating stored configuration
- Package responsibility: React to configuration updates and reload with updated entity references
- Device name changes affect entity_ids only when user explicitly chooses entity renaming in HA UI

**Friendly Name vs Entity ID Changes**:
- **Friendly name override**: User changes display name in HA, entity_id remains unchanged - no action required by SPAN HA Integration or package
- **Entity ID change**: User changes actual entity_id - both SPAN HA Integration and package must update their respective configurations and references
- Only entity_id changes trigger configuration updates and component notifications

### 6. Configuration Extension Interface

**Direct Storage Interface**:
- SPAN HA Integration updates configurations through direct calls to package storage interface
- No separate notification mechanism required - package knows changes immediately
- Package handles both storage updates and sensor lifecycle management in same operation

**Configuration Management Interface**:
```python
# SPAN HA Integration creates/updates configurations directly
await storage_manager.add_sensor(config_uuid, sensor_key, sensor_definition)
await storage_manager.update_sensor(config_uuid, sensor_key, updated_definition)  
await storage_manager.remove_sensor(config_uuid, sensor_key)
await storage_manager.remove_configuration(config_uuid)

# Package validates and applies changes atomically
# No additional notification calls needed
```

**Interface Benefits**:
- **Atomic operations** - storage update and sensor management happen together
- **Immediate validation** - package can validate and reject invalid configurations at call time
- **Simple SPAN HA Integration workflow** - one call handles complete operation
- **Consistent state** - no possibility of storage/sensor state mismatch

**SPAN HA Integration Workflow**:
1. SPAN HA Integration determines configuration change needed
2. SPAN HA Integration calls appropriate package storage interface method
3. Package validates configuration and updates storage
4. Package creates/updates/removes synthetic sensors as needed
5. Package returns success/failure to SPAN HA Integration

**Error Handling**:
- Package validates sensor definitions during interface calls
- Invalid configurations rejected immediately with detailed error messages
- SPAN HA Integration handles validation failures and can retry with corrected definitions

**Responsibilities**:
- **SPAN HA Integration**: Owns storage, manages locks, updates configuration, notifies package
- **Package**: Uses callback interface for storage updates, responds to change notifications
- **Storage as truth**: All updates go through storage first, then notification

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

### 3. Multiple Configuration Lifecycle

**Entity ID Conflict Prevention**:
- SPAN HA Integration will not allow sensor key conflicts within its own domain
- Each synthetic sensor definition references unique entity_ids within the SPAN HA Integration's scope
- SPAN HA Integration responsibility to ensure no duplicate sensor keys for same device across multiple configurations

**Home Assistant Entity ID Resolution**:
- If entity_id conflicts occur despite SPAN HA Integration controls, HA automatically resolves with suffixes (`_2`, `_3`, etc.)
- Package relies on HA's built-in conflict resolution mechanism
- No special conflict handling required in package - HA handles gracefully

**Multiple Configuration Behavior**:
- Each configuration (UUID) operates independently with separate storage
- Sensors from different configurations appear as separate entities in HA
- No merging of sensors across configurations - each maintains distinct identity
- Package may manage multiple configurations simultaneously for same SPAN HA Integration

**Cross-Domain Entity References**:
- Synthetic formulas may reference entities from other domains (e.g., weather sensors)
- Entity_id uniqueness enforced globally by HA across all domains
- Package normalizes all entity references regardless of source domain
- SPAN HA Integration provides complete entity_ids, package handles normalization uniformly

**Configuration Coordination**:
- SPAN HA Integration generates unique config UUIDs and manages configuration lifecycle
- Package handles storage and entity management for each configuration independently
- No coordination required between multiple configurations at package level# Home Assistant Synthetic Sensors Integration Requirements

This document outlines the requirements for integrating the `ha-synthetic-sensors` package with Home Assistant integrations, focusing on device-aware entity naming, local storage management, and runtime synchronization.

## Overview

The synthetic sensors package enables the SPAN HA Integration to create calculated sensors that appear as native entities under the SPAN HA Integration's devices. The system uses Home Assistant's local storage for configuration persistence and implements automatic entity rename synchronization.

## Configuration Schema Authority

**YAML is the Authoritative Definition**: All configuration schema requirements are defined in YAML format as the authoritative contract. JSON serves as the internal storage representation derived from the YAML schema.

**Schema Relationship**:
- **YAML Schema**: Authoritative definition for all configuration requirements
- **JSON Schema**: Derived directly from YAML schema for internal storage
- **Schema Evolution**: Changes to storage requirements start with YAML schema updates
- **Derivation Principle**: JSON structure always follows YAML structure exactly
- **Contract Source**: YAML defines the interface contract between integration and package

**Format Roles**:
- **YAML**: User-facing configuration format and authoritative schema definition
- **JSON**: Internal storage format derived from YAML schema
- **Mapping**: One-to-one bidirectional transformation without data loss

## Architecture Components

1. **SPAN HA Integration**: Manages devices, native sensors, and synthetic sensor definitions
2. **Synthetic Sensors Package**: Creates and manages calculated sensors, handles device prefix resolution
3. **Local Storage**: JSON-based configuration persistence in HA storage
4. **YAML Services**: Import/export interface for user configuration management

## Sensor Naming Contract

### Device Identifier vs Device Name Relationship

**Core Concept**: The SPAN HA Integration uses two distinct pieces of information for device management:

1. **Device ID**: Immutable unique identifier (serial number, MAC address, etc.)
   - Used for device registry association and grouping
   - Never changes during device lifetime
   - Example: `"nj-2316-005k6"` (SPAN panel serial number)

2. **Device Name**: User-configurable display name
   - Used as prefix for sensor naming
   - Can be changed by user (triggers device renaming which updates all associated sensor entity_id prefixes)
   - Gets slugified for entity_id prefix
   - Example: "Span Panel 1" → `span_panel_1`

**Unique ID Considerations**: Each sensor must have a stable unique_id for Home Assistant entity registry that preserves statistics across device name changes. The unique_id pattern should incorporate the immutable device_identifier while the entity_id uses the mutable device_name prefix. 

**SPAN Synthetic Sensor Unique ID Pattern**: `span_{serial_number}_{sensor_key}`
- Example: `span_nj2316005k6_solar_total`
- Same pattern as native sensors, using YAML sensor key as identifier
- Pattern remains stable across all versions regardless of entity_id naming changes
- Serial number ensures uniqueness across multiple devices
- See SPAN Unique Key Compatibility documentation for complete unique_id patterns and stability requirements.

### YAML Configuration Example

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

**Key Distinctions**:
- **`device_identifier`** (YAML field): Raw device identifier for device registry lookup (`nj-2316-005k6`)
- **`device_id`** (conceptual): Fully qualified device identifier with device name prefix in other contexts

**Entity ID Behavior**:
- **When `entity_id` is provided**: Package uses the explicit entity_id as-is, no validation against device prefix patterns
- **When `entity_id` is omitted**: Package must look up device name from `device_identifier` and derive entity_id prefix (`sensor.{derived_prefix}_{sensor_key}`)
- **Existing entity handling**: If entity with specified `entity_id` already exists, HA updates it (standard HA behavior)
- **No validation enforcement**: Package trusts explicit entity_id values completely, allowing maximum integration flexibility

**Entity ID Override Example**:
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

### Package Implementation Requirements

**Device Identifier Format**:
- Package expects `device_identifier` as a single string value (e.g., `"nj-2316-005k6"`)
- Package does NOT handle HA device identifier tuple format `(domain, identifier)`
- Integration must provide only the identifier portion, not the full tuple

**Device Registry Lookup**:
- Package searches for devices where `device_identifier` matches any identifier in the device's identifier set
- Lookup is scoped to the integration's config entry context (implicit domain scoping)
- Package matches against the second element of identifier tuples: `(domain, identifier)`

**Error Handling for Missing Devices**:
- **Missing device_identifier**: Raise configuration error, fail sensor creation
- **No matching device found**: Raise configuration error, fail sensor creation
- **No fallback behavior**: Package must not fall back to default prefixes or create orphaned sensors
- **Clear error messages**: Include device_identifier value and available devices in error reporting

**Multiple Device Identifiers**:
- HA devices can have multiple identifier tuples: `[("domain1", "id1"), ("domain2", "id2")]`
- Package matches when `device_identifier` equals the identifier portion of ANY tuple
- First matching device is used (devices should have unique identifiers within config entry scope)

**Integration Domain Scoping**:
- Device lookup is implicitly scoped to the integration's config entry
- Package receives context from integration during setup (storage key, config entry)
- No cross-integration device matching to prevent conflicts

## Identifier Derivation Patterns

The following table shows how device and sensor identifiers are derived from source data:

| Component | Type | Source Data | Derivation | Example Result |
|-----------|------|-------------|------------|----------------|
| **Device** | Domain | Integration | Fixed per integration | `span_panel` |
| | Device ID | Panel API | Serial number from panel | `"nj-2316-005k6"` |
| | Device Name | User Config | User-configurable display name | `"Span Panel 1"` |
| | Device Name Prefix | Device Name | Slugified device name | `span_panel_1` |
| **Native Sensor*** | Circuit ID | Panel API | `circuits[].id` field | `"0dad2f16cd514812ae1807b0457d473e"` |
| | Circuit Name | Panel API | `circuits[].name` field | `"Lights Dining Room"` |
| | Sensor Name | Circuit Name | Slugified circuit name | `lights_dining_room` |
| | API Key | Panel API | Data field key | `instantPowerW` |
| | Suffix | API Key Mapping | Integration-defined mapping | `"instantPowerW": "power"` |
| | **Entity ID** | **Combination** | **`sensor.{prefix}_{sensor_name}_{suffix}`** | **`sensor.span_panel_1_lights_dining_room_power`** |
| | **Unique ID** | **Combination** | **`span_{serial}_{circuit_id}_{api_key}`** | **`span_nj2316005k6_0dad2f16cd514812ae1807b0457d473e_instantPowerW`** |
| **Synthetic Sensor*** | Synthetic Key | YAML Config | User-defined sensor key | `solar_total` |
| | **Entity ID** | **Combination** | **`sensor.{prefix}_{synthetic_key}`** | **`sensor.span_panel_1_solar_total`** |
| | **Unique ID** | **Combination** | **`span_{serial}_{sensor_key}`** | **`span_nj2316005k6_solar_total`** |

**Key Notes:**
- **Domain**: Used by integration to distinguish its devices in HA, not used by package
- **Device ID**: Immutable across device lifetime, used for HA device registry association
- **Device Name Prefix**: Mutable, drives entity_id prefixes, changes trigger entity_id updates
- **Circuit ID**: UUID from panel API, provides unique_id stability for native sensors
- **API Key**: Raw field name from panel, preserved in unique_id for compatibility
- **Suffix**: Human-readable mapping of API keys for entity_id readability

*Native Sensor: Created and managed directly by the integration. Synthetic Sensor: Defined by the integration but created and managed by the synthetic package.

### Sensor Naming Pattern

**SPAN HA Integration Native Sensors**: `sensor.{device_name_prefix}_{sluggified_sensor_name}`
- Example: `sensor.span_panel_1_instantaneous_power`
- Device name prefix derived from SPAN HA Integration-controlled entity_id pattern (not HA's default slugified friendly name)
- SPAN HA Integration sets entity_id directly and may provide user options for entity_id patterns separate from friendly names
- Device name is separate from device_id (immutable unique identifier like serial number)
- Device name can change and triggers child entity device prefix renames (sensor, switch, entity_id prefixes); device_id remains constant for device association
- Automatically renamed when device name changes

**Synthetic Sensors**: `sensor.{device_name_prefix}_{synthetic_key}`
- Example: `sensor.span_panel_1_solar_total`
- Uses same prefix as native sensors for consistency
- Package resolves prefix from device_identifier lookup

## Integration Requirements

### 1. Device Registration and Entity Naming

**Requirement**: Integration establishes device identifier and naming patterns.

**Responsibilities**:
- Register device with unique `device_identifier` in device registry
- Use user-configurable device name for entity prefixes
- Create native sensors following naming pattern
- Ensure device exists before synthetic sensor creation

**Interface Contract**:
- **Device Identifier**: Unique, immutable identifier for device association
- **Device Name**: User-configurable name used for entity prefixes
- **Entity Pattern**: `sensor.{slugified_device_name}_{entity_suffix}`
- **Device Association**: All sensors (native + synthetic) grouped under same device

## Configuration Lifecycle Management

### JSON Storage Ownership Model

**Core Principle**: Integration creates initial configuration, package manages ongoing lifecycle.

**Configuration Roles**:
- **YAML**: User-facing format managed by package for import/export
- **JSON**: Internal storage format with shared lifecycle management
- **Storage Authority**: Package owns configuration updates and maintenance
- **Integration Participation**: Integration can add/remove sensors with notification

### Lifecycle Phases

**Initialization Phase (Integration)**:
- Integration creates initial JSON configuration in HA storage
- Populates default synthetic sensor definitions
- Hands off storage management to package

**Runtime Phase (Package)**:
- Package subscribes to entity registry events
- Package updates JSON when sensors are renamed
- Package maintains formula dependencies and cache synchronization

**Extension Phase (Integration)**:
- Integration adds/removes synthetic sensor definitions
- Integration may refine a synthetic sensor by adding attributes or changing other characteristics
- Integration updates JSON storage directly
- Integration notifies package of configuration changes
- Package responds by updating its artifacts and sensors

### In-Memory Contract

**Shared Principle**: No persistent in-memory JSON representation

**Requirements**:
- Neither component maintains cached JSON configuration
- All configuration access goes through HA storage interface
- Changes are atomic and immediately persisted
- Configuration reads are performed on-demand
- Prevents out-of-sync issues between components

## Integration Requirements

### 1. Device Registration and Entity Naming

**Requirement**: Integration establishes device identifier and naming patterns.

**Responsibilities**:
- Register device with unique device_id in device registry
- Use user-configurable device name for entity prefixes
- Create native sensors following naming pattern
- Create initial JSON configuration for synthetic sensors

**Interface Contract**:
- **Device ID**: Unique, immutable identifier for device association
- **Device Name**: User-configurable name used for entity prefixes
- **Entity Pattern**: `sensor.{slugified_device_name}_{entity_suffix}`
- **Configuration Handoff**: Create initial JSON, transfer ownership to package

### 2. Initial Configuration Creation

**Requirement**: Integration creates initial JSON configuration with YAML mapping.

**Responsibilities**:
- Create unique storage key per device
- Initialize storage with default synthetic sensor definitions  
- Use JSON structure with one-to-one mapping to YAML format
- Transfer configuration management to package after creation

**Interface Contract**:
- **Storage Key Format**: `{domain}_synthetic_sensors_{config_uuid}`
- **JSON Schema**: Direct mapping from existing YAML configuration schema with configuration UUID
- **Initial Population**: Create useful default synthetic sensors
- **Ownership Transfer**: Package takes over configuration maintenance after handoff
- **Multiple Configurations**: Integration can create multiple configurations (integration defaults, user customs, etc.)

### Configuration Organization and Storage

**Package-Owned Storage Management**:
- Package owns and manages all storage complexity including normalization and entity reference management
- Integration creates configuration UUIDs and sensor definitions, delegates storage to package
- Package handles entity reference normalization to optimize for efficient rename operations
- Integration provides declarative sensor definitions, package determines optimal storage structure

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

### 3. Storage Manager Interface Lifecycle

**Integration Lifecycle Alignment**:
- Storage manager created once per integration instance during integration setup
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

**Lifecycle Benefits**:
- **Single manager per integration** - one storage manager handles all configurations
- **Efficient resource usage** - reuse connection and context across operations  
- **Consistent state management** - same manager maintains coherent view of all configurations
- **Simple cleanup** - storage manager cleanup follows integration uninstall/shutdown

### 4. Entity ID Override with Device Association

**Device Association Independence**:
- Package associates sensors with devices using `device_identifier` regardless of entity_id format
- No validation or enforcement of device prefix patterns in entity_id
- Integration controls entity_id completely, including legacy cases without device prefixes

**Integration Device Association**:
- Integration provides `device_identifier` when it wants sensor associated with its devices
- All integration-managed synthetic sensors include `device_identifier` for device grouping
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

### 5. YAML Import/Export with Multiple Configurations

**Single Configuration Operations**:
- YAML export/import operates on single configuration per service call
- Integration specifies target configuration using config_uuid parameter
- YAML content returned directly from export method invocation
- Integration controls which configurations to export/import

**YAML Service Interface**:
```python
# Export specific configuration to YAML
yaml_content = await storage_manager.export_yaml(config_uuid="uuid1")

# Import YAML to specific configuration
await storage_manager.import_yaml(config_uuid="uuid1", yaml_content=yaml_string)

# Integration manages multiple configurations as needed
for config_uuid in self.managed_configurations:
    if user_requests_export(config_uuid):
        yaml_content = await self.storage_manager.export_yaml(config_uuid)
        save_user_file(f"{config_name}.yaml", yaml_content)
```

**YAML Export/Import Benefits**:
- **Targeted operations** - export/import exactly the configuration needed
- **Synchronous response** - YAML content returned directly from method call
- **Clear scope** - one configuration per operation, no ambiguity about content
- **Integration control** - integration decides export/import strategy for multiple configurations

**YAML Structure Consistency**:
- Exported YAML matches configuration schema used for integration definitions
- Import validates YAML structure and converts to normalized storage format
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

**Phase 1 Success Criteria**:
- Integration can pass domain and device_identifier to package
- Package correctly resolves device names and generates entity_id prefixes
- Synthetic sensors appear under correct devices in HA UI
- Entity_ids follow consistent device prefix patterns
- Explicit entity_id overrides work correctly

**Phase 1 Validation**:
- Verify device association in HA device registry
- Confirm entity_id patterns match device naming
- Test with both derived and explicit entity_ids
- Validate cross-device configurations work properly

**Configuration Schema for Integration**:
```yaml
# Integration provides this structure to package
config_id: "uuid1"                     # Required: unique configuration identifier  
name: "Integration Solar Defaults"     # Required: human readable configuration name
version: "1.0"                         # Required: schema version
sensors:
  solar_total:
    device_identifier: nj-2316-005k6
    formula: "solar_power + weather_adjustment"
    variables:
      solar_power: "sensor.span_panel_1_solar_power"      # Package normalizes
      weather_adjustment: "sensor.weather1.ambient_temp"  # Package normalizes
```

**Storage Normalization Requirements**:
- **REQUIRED: Entity reference normalization** - package MUST convert entity_ids to internal UUIDs/references within each configuration
- **REQUIRED: Internal reference system** - package creates its own UUID system, independent of HA entity registry UUIDs
- **REQUIRED: Single update point** - entity renames MUST update only the entity reference table, never scan formulas
- **REQUIRED: Efficient rename operations** - storage structure MUST support O(1) entity rename updates across all configurations
- **REQUIRED: Referential integrity** - package MUST validate all entity references exist and maintain consistency
- **Entity reference table per configuration** - each configuration maintains its own entity_id to internal UUID mapping
- **Self-contained normalization** - package controls entire reference system without dependency on HA internals

**Normalization Structure Example**:
```json
{
  "config_id": "uuid1",
  "name": "Solar Defaults",
  "entity_references": {
    "ref_001": {
      "entity_id": "sensor.span_panel_1_solar_power",
      "description": "Solar panel power"
    },
    "ref_002": {
      "entity_id": "sensor.weather1.ambient_temp",
      "description": "Weather temperature"  
    }
  },
  "sensors": {
    "solar_efficiency": {
      "formula": "solar_power / weather_temp",
      "variables": {
        "solar_power": "ref_001",    // Internal UUID reference
        "weather_temp": "ref_002"    // Internal UUID reference
      }
    }
  }
}
```

**Entity Rename Handling**:
- Entity rename updates only `entity_references` table: `ref_001.entity_id = "new_entity_id"`
- All formulas automatically use updated entity_id through reference system
- No formula scanning or modification required

**Integration Responsibilities**:
- Generate unique config_id (UUID) for each configuration
- Provide sensor definitions with entity_ids in variables/formulas
- Request configuration operations (create, update, remove) through package interface
- Handle device lifecycle and notify package of device-related changes

**Package Responsibilities**:
- Accept declarative sensor definitions from integration
- Normalize entity references for efficient rename handling
- Manage storage structure and optimization internally
- Provide configuration management interface to integration
- Handle entity rename propagation across all stored configurations

### 2. Device Prefix Resolution Method

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

**Integration Device Naming Requirements**:
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
- Each configuration (UUID) operates independently with separate storage
- Sensors from different configurations appear as separate entities in HA
- No merging of sensors across configurations - each maintains distinct identity
- Package may manage multiple configurations simultaneously for same integration

**Cross-Domain Entity References**:
- Synthetic formulas may reference entities from other domains (e.g., weather sensors)
- Entity_id uniqueness enforced globally by HA across all domains
- Package normalizes all entity references regardless of source domain
- Integration provides complete entity_ids, package handles normalization uniformly

**Configuration Coordination**:
- Integration generates unique config UUIDs and manages configuration lifecycle
- Package handles storage and entity management for each configuration independently
- No coordination required between multiple configurations at package level

### 4. Configuration Extension Interface

**Direct Storage Interface**:
- Integration updates configurations through direct calls to package storage interface
- No separate notification mechanism required - package knows changes immediately
- Package handles both storage updates and sensor lifecycle management in same operation

**Configuration Management Interface**:
```python
# Integration creates/updates configurations directly
await storage_manager.add_sensor(config_uuid, sensor_key, sensor_definition)
await storage_manager.update_sensor(config_uuid, sensor_key, updated_definition)  
await storage_manager.remove_sensor(config_uuid, sensor_key)
await storage_manager.remove_configuration(config_uuid)

# Package validates and applies changes atomically
# No additional notification calls needed
```

**Interface Benefits**:
- **Atomic operations** - storage update and sensor management happen together
- **Immediate validation** - package can validate and reject invalid configurations at call time
- **Simple integration workflow** - one call handles complete operation
- **Consistent state** - no possibility of storage/sensor state mismatch

**Integration Workflow**:
1. Integration determines configuration change needed
2. Integration calls appropriate package storage interface method
3. Package validates configuration and updates storage
4. Package creates/updates/removes synthetic sensors as needed
5. Package returns success/failure to integration

**Error Handling**:
- Package validates sensor definitions during interface calls
- Invalid configurations rejected immediately with detailed error messages
- Integration handles validation failures and can retry with corrected definitions

### 3. Configuration Extension Interface

**Requirement**: Integration can add/remove synthetic sensors with package notification.

**Responsibilities**:
- Update JSON storage when adding/removing synthetic sensors
- Notify package of configuration changes
- Maintain consistency with existing sensor definitions
- Follow established naming and schema patterns

**Interface Contract**:
- **Direct Storage Access**: Integration updates JSON storage directly
- **Change Notification**: Inform package of modifications via defined interface
- **Schema Compliance**: New sensors must follow existing JSON schema
- **Package Response**: Package updates artifacts and sensors after notification

### 3. Data Provider Implementation

**Requirement**: Integration provides real-time data for synthetic sensor evaluation.

**Responsibilities**:
- Implement data provider callback for integration-managed entities
- Register entities that integration can provide data for
- Handle both integration-native and HA entity references in formulas
- Maintain consistent data availability during sensor evaluation

**Interface Contract**:
- Data provider callback returns value and existence status
- Entity registration set must be maintained and updated
- Integration entities take precedence over HA state queries
- No fallback mechanism - strict data source routing

### 4. Runtime Entity Rename Handling

**Requirement**: Integration must handle entity renames for its native sensors.

**Responsibilities**:
- Monitor entity registry events for integration entities
- Update internal sensor mappings when entities are renamed
- Coordinate with synthetic sensors package for dependency updates
- Maintain data provider entity registration accuracy

**Interface Contract**:
- Extend base `EntityRenameHandler` class
- Filter renames relevant to integration entities
- Update all internal references to renamed entities
- Notify package of entity registration changes

## Synthetic Sensors Package Requirements

### 1. Configuration Lifecycle Management

**Requirement**: Package owns configuration maintenance after initial handoff from integration.

**Responsibilities**:
- Take ownership of JSON configuration after integration creates it
- Subscribe to entity registry events affecting synthetic sensors
- Update JSON configuration when sensors are renamed
- Maintain formula dependencies and cache synchronization
- Respond to integration notifications of configuration changes

**Interface Contract**:
- **Ownership Model**: Package manages configuration after initial creation
- **Event Subscription**: Monitor all entity renames affecting formulas
- **Automatic Updates**: Update JSON when dependencies change
- **Integration Notifications**: Accept and respond to configuration change alerts
- **Storage Authority**: Package is authoritative source for configuration state

### 2. JSON Storage Interface

**Requirement**: Package must read and maintain JSON configuration that directly maps to YAML schema.

**Responsibilities**:
- Read JSON configuration from integration-provided storage key
- Maintain one-to-one mapping between YAML and JSON formats
- Update JSON configuration in response to entity changes
- Handle configuration extensions from integration

**Interface Contract**:
- **Storage Interface**: Accept storage key from integration during setup
- **Schema Mapping**: JSON structure identical to existing YAML schema
- **No In-Memory Caching**: All access goes through HA storage interface
- **Atomic Updates**: Configuration changes are immediately persisted
- **Change Detection**: Respond to both internal and external configuration modifications

### 3. Device Prefix Resolution and Entity Naming

**Requirement**: Package must resolve device name prefixes and create consistently named entities.

**Responsibilities**:
- Lookup device information using `device_identifier` from storage configuration
- Resolve current device name (including user customizations)
- Generate entity IDs that match integration naming pattern
- Update JSON configuration and entity IDs when devices are renamed

**Interface Contract**:
- **Input**: `device_id` from synthetic sensor configuration
- **Lookup**: Device registry query to find associated device
- **Resolution**: Use `device.name_by_user` or `device.name` for prefix
- **Output**: Entity ID following `sensor.{slugified_device_name}_{sensor_key}` pattern
- **Automatic Updates**: Update both entities and JSON when device names change

### 5. YAML Import/Export Services

**Requirement**: Package must provide YAML services for user configuration management.

**Responsibilities**:
- Manage YAML as the user-facing configuration format
- Provide import service to convert YAML to JSON storage configuration
- Provide export service to convert JSON storage configuration to YAML
- Validate imported YAML content and structure
- Trigger sensor reload after configuration import

**Interface Contract**:
- **YAML Authority**: Package owns YAML format definition and management
- **Import Service**: `synthetic_sensors.import_yaml` with yaml_content and storage_key parameters
- **Export Service**: `synthetic_sensors.export_yaml` with storage_key parameter, returns yaml_content
- **Validation**: YAML validation with detailed error reporting
- **Integration**: Automatic sensor reconfiguration after successful import
- **Format Mapping**: Maintain one-to-one correspondence between YAML and JSON

## Integration Sequence

### Setup Phase

1. **Integration**: Register device in device registry
2. **Integration**: Create native sensors with proper entity ID prefixes
3. **Integration**: Initialize local storage with synthetic sensor definitions
4. **Integration**: Setup data provider callback and entity registration
5. **Package**: Read configuration from storage
6. **Package**: Resolve device prefixes from device registry
7. **Package**: Create synthetic sensors with device-aware entity IDs
8. **Both**: Setup entity rename handlers

### Runtime Phase

1. **Integration**: Update live sensor data for data provider
2. **Package**: Evaluate synthetic sensor formulas using mixed data sources
3. **On Entity Rename**:
   - Integration updates native sensor mappings
   - Package updates formula cache and storage configuration
   - Both components re-establish tracking and dependencies

### User Configuration Phase

1. **User**: Export current configuration via `synthetic_sensors.export_yaml`
2. **User**: Modify YAML configuration as needed
3. **User**: Import updated configuration via `synthetic_sensors.import_yaml`
4. **Package**: Validate, persist, and reload synthetic sensors

## Interface Contracts

### EntityRenameHandler Base Class

**Purpose**: Provide common infrastructure for entity rename handling

**Requirements**:
- Subscribe to entity registry update events
- Filter events based on entity relevance
- Provide tracking mechanism for monitored entities
- Abstract interface for rename handling implementation
- Proper lifecycle management (setup/teardown)

### Storage Configuration Schema

**Purpose**: Define structure for local storage configuration with YAML mapping

**Requirements**:
- **Schema Source**: JSON schema derived directly from existing YAML schema
- **One-to-One Mapping**: Every YAML construct has exact JSON equivalent
- **Format Roles**: 
  - YAML: User-facing configuration and import/export format
  - JSON: Internal storage and runtime configuration format
- **Bidirectional Conversion**: Lossless transformation between YAML and JSON
- **Validation Consistency**: Same validation rules apply to both formats
- **Schema Evolution**: Version field supports schema migrations for both formats

### Data Provider Interface

**Purpose**: Allow integration to provide real-time sensor data

**Requirements**:
- Callback function accepting entity_id parameter
- Return structure with value and existence fields
- Entity registration mechanism for provider routing
- No fallback behavior - strict data source separation
- Support for dynamic entity registration updates

## Error Handling Requirements

### Integration Error Handling

**Requirements**:
- Graceful degradation when synthetic sensors fail
- Proper error logging for storage operations
- Fallback behavior for missing device registry entries
- Recovery mechanisms for corrupted storage data

### Package Error Handling

**Requirements**:
- Formula evaluation errors result in "unavailable" state
- Missing entity dependencies handled gracefully
- Storage corruption triggers validation and recovery
- Clear error messages for configuration issues
- Circuit breaker pattern for persistent failures

## Performance Considerations

### Integration Performance

**Requirements**:
- Minimal overhead for data provider callbacks
- Efficient entity registration updates
- Batch processing for multiple entity renames
- Lazy loading of synthetic sensor configurations

### Package Performance

**Requirements**:
- Efficient formula cache invalidation
- Incremental dependency updates
- Optimized device registry lookups
- Minimal storage I/O operations

## Testing Requirements

### Integration Testing

**Focus Areas**:
- Device registration and entity creation sequence
- Data provider callback functionality
- Entity rename handling for native sensors
- Storage initialization and persistence
- Error handling and recovery scenarios

### Package Testing

**Focus Areas**:
- Device prefix resolution from registry
- Storage-based configuration loading
- Entity rename synchronization
- YAML import/export services
- Formula evaluation with mixed data sources
- Performance under load conditions

## Migration Strategy

**For existing YAML-based implementations**:

1. **Phase 1**: Implement storage-based configuration alongside YAML
2. **Phase 2**: Add YAML import service to migrate existing configurations
3. **Phase 3**: Deprecate file-based YAML configuration
4. **Phase 4**: Remove YAML file support, keep import/export services

## Benefits

- **Device-Aware Naming**: Synthetic sensors follow HA device rename conventions
- **Persistent Configuration**: JSON storage survives HA restarts and updates
- **Runtime Synchronization**: Automatic handling of entity renames
- **User Accessibility**: YAML import/export for advanced configuration
- **Integration Flexibility**: Support for mixed data sources and custom calculations
- **Performance**: Efficient formula evaluation and cache management
- **Maintainability**: Clear separation of concerns between integration and package

## Compliance Requirements

### Home Assistant Standards

**Requirements**:
- Follow HA entity naming conventions
- Use proper device registry integration
- Implement standard storage patterns
- Provide appropriate service interfaces
- Support HA configuration validation

### Package Standards

**Requirements**:
- Maintain backward compatibility during migrations
- Provide comprehensive error handling
- Support standard HA logging patterns
- Follow HA async programming patterns
- Implement proper resource cleanup

## Version Compatibility

- **Home Assistant**: 2024.1+
- **Python**: 3.11+
- **Package Version**: 2.0+ (for storage-based configuration)

## Documentation Requirements

### Integration Documentation

**Required Topics**:
- Setup sequence and device registration
- Storage configuration management
- Data provider implementation patterns
- Entity rename handling strategies

### Package Documentation

**Required Topics**:
- Storage-based configuration schema
- Device prefix resolution behavior
- Entity rename synchronization mechanics
- YAML import/export usage patterns
- Performance optimization guidelines

## Support and Maintenance

### SPAN HA Integration Support

**Responsibilities**:
- Maintain device registration accuracy
- Ensure data provider reliability
- Handle storage lifecycle properly
- Provide clear error diagnostics

### Package Support

**Responsibilities**:
- Maintain formula evaluation accuracy
- Ensure rename synchronization reliability
- Provide responsive YAML services
- Handle edge cases gracefully
