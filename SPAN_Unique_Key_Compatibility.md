# SPAN Unique Key Compatibility

Without unique key compatibility an upgrade will create new sensors or will create sensors with '_2' suffix
since the entity id will match but the unique ID will not. This behavior will result in lost statistics
as the new sensor will not match the old sensor with the existing history. The integration has tests
to specifically ensure compatibility from one release to the next.

**Unique IDs vs Entity IDs:**

- **Unique IDs**: Provide statistics continuity, must be migrated and preserved during upgrades
- **Entity IDs**: Primary reference for user templates and UI; Can change based on version and user configuration flags, maybe renamed by user.

## Helper Function Analysis

### Unique ID Helpers (Statistics Continuity)

| Helper Function | Purpose | Pattern | Example Output | Notes |
|-----------------|---------|---------|----------------|-------|
| `build_circuit_unique_id(serial, circuit_id, description_key)` | Pure function for circuit unique IDs | `span_{serial}_{circuit_id}_{suffix}` | `span_abc123_0dad2f16cd514812ae1807b0457d473e_power` | ✅ Follows document pattern |
| `build_panel_unique_id(serial, description_key)` | Pure function for panel unique IDs | `span_{serial}_{suffix}` | `span_abc123_current_power` | ✅ Uses entity ID suffix via `get_panel_entity_suffix()` |
| `build_switch_unique_id(serial, circuit_id)` | Pure function for switch unique IDs | `span_{serial}_relay_{circuit_id}` | `span_abc123_relay_0dad2f16cd514812ae1807b0457d473e` | ✅ Switch-specific pattern |
| `build_binary_sensor_unique_id(serial, description_key)` | Pure function for binary sensor unique IDs | `span_{serial}_{description_key}` | `span_abc123_doorState` | ✅ Binary sensor pattern |
| `build_select_unique_id(serial, select_id)` | Pure function for select unique IDs | `span_{serial}_select_{select_id}` | `span_abc123_select_priority_mode` | ✅ Select-specific pattern |
| `constuct_synthetic_unique_id(serial, sensor_name)` | Pure function for synthetic sensor unique IDs | `span_{serial}_{sensor_name}` | `span_abc123_solar_total_power` | ✅ Synthetic sensor pattern |
| `construct_unmapped_unique_id(span_panel, circuit_number, suffix)` | Unmapped circuit unique IDs | `span_{serial}_unmapped_tab_{circuit_number}_{suffix}` | `span_abc123_unmapped_tab_32_power` | ✅ Unmapped circuit pattern |

### Unique ID Wrapper Helpers (Use Pure Functions Above)

| Helper Function | Purpose | Calls | Notes |
|-----------------|---------|-------|-------|
| `construct_circuit_unique_id(span_panel, circuit_id, description_key)` | Circuit unique ID wrapper | `build_circuit_unique_id()` | ✅ Good wrapper |
| `construct_panel_unique_id(span_panel, description_key)` | Panel unique ID wrapper | `build_panel_unique_id()` | ✅ Now uses correct entity ID suffix |
| `construct_switch_unique_id(span_panel, circuit_id)` | Switch unique ID wrapper | `build_switch_unique_id()` | ✅ Good wrapper |
| `construct_binary_sensor_unique_id(span_panel, description_key)` | Binary sensor unique ID wrapper | `build_binary_sensor_unique_id()` | ✅ Good wrapper |
| `construct_select_unique_id(span_panel, select_id)` | Select unique ID wrapper | `build_select_unique_id()` | ✅ Good wrapper |

### Entity ID Helpers (User-Facing Naming)

| Helper Function | Purpose | Naming Strategy | Configuration Flags | Notes |
|-----------------|---------|-----------------|---------------------|-------|
| `construct_entity_id(coordinator, span_panel, platform, circuit_name, circuit_number, suffix, unique_id)` | Generic circuit entity ID | Circuit name or number based | `USE_CIRCUIT_NUMBERS`, `USE_DEVICE_PREFIX` | ✅ Handles both naming strategies |
| `construct_panel_entity_id(coordinator, span_panel, platform, suffix, unique_id)` | Panel-level entity ID | Always friendly naming | `USE_DEVICE_PREFIX` | ✅ Panel sensors don't have circuits |
| `construct_single_circuit_entity_id(coordinator, span_panel, platform, suffix, circuit_data, unique_id)` | Single circuit entity ID | Circuit name or number based | `USE_CIRCUIT_NUMBERS`, `USE_DEVICE_PREFIX` | ✅ For individual circuits |
| `construct_multi_circuit_entity_id(coordinator, span_panel, platform, suffix, circuit_numbers, friendly_name, unique_id)` | Multi-circuit entity ID | Circuit numbers or friendly name | `USE_CIRCUIT_NUMBERS`, `USE_DEVICE_PREFIX` | ✅ For combining circuits |
| `construct_solar_synthetic_entity_id(coordinator, span_panel, platform, suffix, friendly_name, unique_id, leg1, leg2)` | Solar synthetic entity ID | Calls multi-circuit helper | `USE_CIRCUIT_NUMBERS`, `USE_DEVICE_PREFIX` | ✅ Wrapper for solar case |
| `construct_unmapped_entity_id(span_panel, circuit_id, suffix)` | Unmapped circuit entity ID | Always device prefix + circuit_id | None (always device prefix) | ✅ Unmapped always visible |

### Backing Entity Helpers (Internal References)

| Helper Function | Purpose | Pattern | Example Output | Notes |
|-----------------|---------|---------|----------------|-------|
| `construct_backing_entity_id(span_panel, circuit_id, suffix)` | Internal backing entity references | `span_{serial}_{circuit_id}_backing_{suffix}` | `span_abc123_0_backing_current_power` | ✅ Follows document pattern |

### Friendly Name Helpers

| Helper Function | Purpose | Notes |
|-----------------|---------|-------|
| `construct_panel_friendly_name(description_name)` | Panel sensor friendly names | ✅ Simple string conversion |
| `construct_status_friendly_name(description_name)` | Status sensor friendly names | ✅ Simple string conversion |
| `construct_unmapped_friendly_name(circuit_number, sensor_description_name)` | Unmapped circuit friendly names | ✅ Format: "Unmapped Tab X Name" |

### Utility Helpers

| Helper Function | Purpose | Notes |
|-----------------|---------|-------|
| `get_user_friendly_suffix(description_key)` | Convert API keys to user-friendly suffixes | ✅ Used by build functions |
| `get_circuit_number(circuit)` | Extract circuit number from circuit object | ✅ Gets tab position |
| `get_friendly_name_from_registry(hass, unique_id, default_name)` | Check for user customizations | ✅ Respects user changes |

### Redundant/Problematic Helpers

| Helper Function | Issue | Recommendation |
|-----------------|-------|----------------|
| ~~`construct_sensor_manager_unique_id(serial_number, circuit_id, description_key)`~~ | ~~Duplicates circuit/panel unique ID logic~~ | ✅ **REMOVED** - functionality covered by existing helpers |

### Previously Missing Helpers (Now Resolved)

| Needed Helper | Purpose | Pattern | Status |
|---------------|---------|---------|--------|
| `construct_circuit_backing_entity_id()` | Circuit backing entities | `span_{serial}_{circuit_id}_backing_{description_key}` | ✅ **NOT NEEDED** - covered by `construct_backing_entity_id()` |
| `construct_panel_backing_entity_id()` | Panel backing entities | `span_{serial}_backing_{description_key}` | ✅ **NOT NEEDED** - covered by `construct_backing_entity_id()` |

**Implementation**: Panel unique ID construction now uses `get_panel_entity_suffix()` which provides direct API-to-entity-suffix mapping for consistency.

**How circuit_id is determined:**

- The `circuit_id` is taken directly from the `id` field in each circuit object returned by the SPAN panel API.
- This value is a UUID-style string (e.g., "0dad2f16cd514812ae1807b0457d473e").
- For example, if the API returns:

```json
"circuits": {
  "0dad2f16cd514812ae1807b0457d473e": {
    "id": "0dad2f16cd514812ae1807b0457d473e",
    "name": "Lights Dining Room",
    ...
  }
}
```

- The unique_id for a power sensor on this circuit would be:

```text
span_{serial_number}_0dad2f16cd514812ae1807b0457d473e_instantPowerW
```

- The SPAN HA Integration always uses the exact value of the `id` field as the circuit_id in the unique_id pattern.

**Implications for unique_id stability:**

- The unique_id for each sensor is stable as long as the panel API provides a stable `circuit_id` for each circuit.
- The SPAN HA Integration does not invent or remap circuit_ids; it uses what the panel API provides.

## Integration Defined Circuit Entities

**New Installation Unique ID Pattern:**

```text
span_{serial_number}_{circuit_id}_{description_key}
```

**Examples:**

- `span_abc123_0dad2f16cd514812ae1807b0457d473e_power`
- `span_abc123_0dad2f16cd514812ae1807b0457d473e_energy_produced`
- `span_abc123_0dad2f16cd514812ae1807b0457d473e_energy_consumed`
- `span_nj-2316-005k6_unmapped_tab_32_power`
- `span_nj-2316-005k6_unmapped_tab_32_energy_produced`

**Implementation:** Native SPAN HA Integration. Unique ID patterns for existing installations
depend on multiple factors including installation history and migration state.
New installations use circuit_id based patterns for consistency and migrate old patterns with config schema v2.0.

## Synthetic Sensors

Synthetic circuits use the sensor top level key as the unique ID.  Whatever that senosr key reflects
is directly created in the registry as the unique ID.  As seen in the examples for 'Regular Circuits'
the unique ID is generated from the span-panel-api package sensors directly reflecting what the SPAN
panel returns for circuit data. User defined circuits are hand crafted but again these sensor keys must be unique.

## Integration-Managed Multi-Tab/240V Synthetics

The SpanPanel integration allows configuration of synthetic sensors that combine two (or more) tabs (different phases) to produce a 240V measurement—such as summing two 120V legs for power and energy. This is commonly used for solar, but can also be used for other multi-tab circuits (e.g., 240V appliances).

The unique key for these synthetic sensors is the sensor key at the top level of the YAML/config. The unique ID and entity_id logic for these sensors is now consistent with all other synthetic sensors, following the standard patterns described above. This ensures stability and compatibility for statistics and migration.

### Legacy Solar Sensors (Pre-v1.2.0)

**Legacy Solar Sensor Unique ID Pattern:**

```text
span_{serial_number}_synthetic_{leg1}_{leg2}_{yaml_key}
```

**Migration Behavior:**

Pre v1.2.0 Legacy HA config version is 1.0
Post v1.2.0 HA config version is 2.0

### New Installation

**Unique ID Pattern:** `span_{serial_number}_{circuit_id}_{description_key}`

| Circuit Type | Unique ID Example | Description |
|--------------|-------------------|-------------|
| **Named Circuits** | `span_abc123_0dad2f16cd514812ae1807b0457d473e_power` | Kitchen outlets on a circuit |
| **Named Circuits** | `span_abc123_0dad2f16cd514812ae1807b0457d473e_energy_produced` | Solar on a circuit |
| **Switch Entities** | `span_abc123_0dad2f16cd514812ae1807b0457d473e_relay_1` | Circuit breaker control |

A backing entity should follow the same pattern in order to map to the synthetic that is services:
span_{serial_number}_{circuit_id}_backing_{description_key}

### Unmapped Tab Entities (v1.2.0+)

**Unique ID Pattern:** `span_{serial_number}_unmapped_tab_{tab_number}_{description_key}`

| Circuit Type | Unique ID Example | Description |
|--------------|-------------------|-------------|
| **Unmapped Tab Power** | `span_nj-2316-005k6_unmapped_tab_32_power` | Unmapped breaker position 32 power |
| **Unmapped Tab Energy** | `span_nj-2316-005k6_unmapped_tab_32_energy_produced` | Unmapped breaker position 32 energy produced |
| **Unmapped Tab Energy** | `span_nj-2316-005k6_unmapped_tab_32_energy_consumed` | Unmapped breaker position 32 energy consumed |

**Unmapped Circuit Special Characteristics:**

- **Provided by**: span-panel-api package, using panel level where actual circuits are not provided by the panel
- **Circuit Source**: Created from `circuit_id` values like `"unmapped_tab_32"` returned by the panel API
- **Native Sensors**: These are integration provided circuit sensors, not synthetic sensors
- **Naming Stability**: Never subject to entity ID naming pattern changes
- **Visibility**: Not user visible - marked as invisible in Home Assistant UI (`entity_registry_visible_default=False`)
- **Purpose**: Provide operands for synthetic sensor calculations like solar or user define synthetics
- **Setup Timing**: Created and added to HA **before** synthetic sensors to ensure proper dependency order

### Panel-Level Entities (All Versions)

Panel level circuits are provided directly by the integration and are not themselves synthetics

**Unique ID Pattern:** `span_{serial_number}_{sensor_key}_{suffix}`

| Entity Type | Unique ID Example | Description |
|-------------|-------------------|-------------|
| **Panel Power** | `span_abc123_current_power` | Main panel power |
| **Panel Status** | `span_abc123_dsm_state` | Demand side management state |
| **Panel Info** | `span_abc123_softwarever` | Panel software version |
| **Door State** | `span_abc123_doorstate` | Panel door open/closed |

### Synthetic Sensors (v1.2.0+)

**Unique ID Pattern:** `span_{serial_number}_{sensor_key}`

| Sensor Type | Unique ID Example | Description |
|-------------|-------------------|-------------|
| **Solar Total** | `span_abc123_solar_total_power` | Combined solar power |
| **Backup Circuits** | `span_abc123_backup_circuits_power` | Backup circuit total |
| **Custom Calculation** | `span_abc123_whole_house_efficiency` | User-defined calculation |

## Sensor Setup Timing and Dependencies

**Timing Requirements:**

The SPAN HA Integration must ensure proper setup of the device and unmapped circuits first order to prevent startup
errors where synthetic sensors reference unavailable entities.

**Setup Sequence (v2.1.0+):**

1. The device must be configured first so that synthetics can look up the device name as sensor prefix
2. Create all native sensors (panel-level, unmapped tabs, hardware status) that could be used in synthetic references
3. Call `async_add_entities(entities)` to register native sensors
4. Set up synthetic sensors that depend on the now-available device and native sensors

**Dependency Hierarchy:**

```text
Native Sensors (SPAN Integration)
├── Device
├── Panel-level sensors (current_power, dsmState, etc.)
├── Unmapped tab sensors (unmapped_tab_32_power, etc.)
└── Hardware status sensors (doorState, etc.)
    ↓
Synthetic Sensors (ha-synthetic-sensors)
├── Solar inverter calculations (depends on unmapped tabs)
└── Custom calculations (depends on any native sensors)
```
