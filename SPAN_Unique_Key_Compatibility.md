# SPAN Unique Key Compatibility

Without unique key compatibility an upgrade will create new sensors or will create sensors with '\_2' suffix since the entity
id will match but the unique ID will not. This behavior will result in lost statistics as the new sensor will not match the
old sensor with the existing history. The integration has tests to specifically ensure compatibility from one release to the
next.

**Unique IDs vs Entity IDs:**

- **Unique IDs**: Provide statistics continuity, must be migrated and preserved during upgrades
- **Entity IDs**: Primary reference for user templates and UI; Can change based on version and user configuration flags,
  maybe renamed by user.

## Helper Function Analysis

### Unique ID Helpers (Statistics Continuity)

| Helper Function                                                | Purpose                                       | Pattern                               | Example Output                                       | Notes                                                         |
| -------------------------------------------------------------- | --------------------------------------------- | ------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| `build_circuit_unique_id(serial, circuit_id, description_key)` | Pure function for circuit unique IDs          | `span_{serial}_{circuit_id}_{suffix}` | `span_abc123_0dad2f16cd514812ae1807b0457d473e_power` | Suffix comes from `get_user_friendly_suffix(description_key)` |
| `build_panel_unique_id(serial, description_key)`               | Pure function for panel unique IDs            | `span_{serial}_{entity_suffix}`       | `span_abc123_current_power`                          | Entity suffix via `get_panel_entity_suffix(description_key)`  |
| `build_switch_unique_id(serial, circuit_id)`                   | Pure function for switch unique IDs           | `span_{serial}_relay_{circuit_id}`    | `span_abc123_relay_0dad2f16cd514812ae1807b0457d473e` |                                                               |
| `build_binary_sensor_unique_id(serial, description_key)`       | Pure function for binary sensor unique IDs    | `span_{serial}_{description_key}`     | `span_abc123_doorState`                              |                                                               |
| `build_select_unique_id(serial, select_id)`                    | Pure function for select unique IDs           | `span_{serial}_select_{select_id}`    | `span_abc123_select_priority_mode`                   |                                                               |
| `construct_synthetic_unique_id(serial, sensor_name)`           | Pure function for synthetic sensor unique IDs | `span_{serial}_{sensor_name}`         | `span_abc123_solar_total_power`                      | `sensor_name` already includes suffix (e.g., `..._power`)     |

### Entry-Aware Unique ID Helpers (Live vs Simulator)

These helpers automatically choose the per-entry device identifier used across unique_ids:

- Live panels: true panel serial number
- Simulator entries: slugified device name (prevents cross-entry collisions)

| Helper Function                                | Calls/Behavior                                                                   | Notes                               |
| ---------------------------------------------- | -------------------------------------------------------------------------------- | ----------------------------------- |
| `construct_panel_unique_id_for_entry(...)`     | Uses `_get_device_identifier_for_unique_ids(...)` → `build_panel_unique_id(...)` | Entry-aware device identifier       |
| `construct_circuit_unique_id_for_entry(...)`   | Entry-aware identifier → `build_circuit_unique_id(...)`                          |                                     |
| `build_switch_unique_id_for_entry(...)`        | Entry-aware identifier → `build_switch_unique_id(...)`                           |                                     |
| `build_select_unique_id_for_entry(...)`        | Entry-aware identifier → `build_select_unique_id(...)`                           |                                     |
| `build_binary_sensor_unique_id_for_entry(...)` | Entry-aware identifier → `build_binary_sensor_unique_id(...)`                    |                                     |
| `construct_synthetic_unique_id_for_entry(...)` | Entry-aware identifier → `construct_synthetic_unique_id(...)`                    | Used for synthetic YAML sensor keys |

### Suffix Mapping Helpers

- `get_user_friendly_suffix(description_key)` → general, consistent suffixes for circuits and some panel sensors
- `get_panel_entity_suffix(description_key)` → panel-specific mapping used for panel unique_id/entity suffixes

Examples:

- `instantPowerW` → `power`
- `producedEnergyWh` → `energy_produced`
- Panel mapping: `instantGridPowerW` → `current_power`, `dsmState` → `dsm_state`

### Entity ID Helpers (User-Facing Naming)

Entity IDs respect user customizations by checking the registry first when `unique_id` is provided. They also honor
integration options like `USE_DEVICE_PREFIX` and `USE_CIRCUIT_NUMBERS`.

| Helper Function                                                                                                   | Purpose                               | Key Behaviors                                                                              |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------ |
| `construct_entity_id(...)`                                                                                        | Generic circuit entity IDs            | Device prefix optional; circuit numbers vs friendly name; avoids duplicate trailing suffix |
| `construct_panel_entity_id(...)`                                                                                  | Panel-level entity IDs                | Device prefix optional; registry lookup by `unique_id`                                     |
| `construct_single_circuit_entity_id(...)`                                                                         | Single-circuit entity IDs             | Circuit numbers vs friendly name, device prefix optional                                   |
| `construct_multi_circuit_entity_id(...)`                                                                          | Multi-circuit (e.g., 240V) entity IDs | Uses tab list or friendly name; device prefix optional; registry lookup by `unique_id`     |
| `construct_panel_synthetic_entity_id(...)`                                                                        | Panel synthetic entity IDs            | Device prefix optional; registry lookup by `unique_id`                                     |
| `construct_240v_synthetic_entity_id(...)`, `construct_120v_synthetic_entity_id(...)`                              | Synthetic circuit entity IDs          | Uses tab numbers and friendly name                                                         |
| `construct_multi_tab_entity_id_from_key(coordinator, span_panel, platform, sensor_key, sensor_config, unique_id)` | Entity ID from synthetic key/config   | Parses tabs attribute, solar keys, or name to dispatch to correct helper                   |

### Backing Entity Helpers (Internal References)

| Helper Function                                | Purpose                            | Pattern                                                        | Example Output                               | Notes                               |
| ---------------------------------------------- | ---------------------------------- | -------------------------------------------------------------- | -------------------------------------------- | ----------------------------------- |
| `construct_backing_entity_id(span_panel, ...)` | Internal backing entity references | `sensor.span_{serial}_{circuit_id_or_0}_backing_{suffix}`      | `sensor.span_abc123_0_backing_current_power` | Not registered; used only in YAML   |
| `construct_backing_entity_id_for_entry(...)`   | Entry-aware backing IDs            | `sensor.span_{identifier}_{circuit_id_or_0}_backing_{suffix}`  | `sensor.span_simdev_0_backing_current_power` | Simulator-safe identifier           |
| `construct_unmapped_unique_id(...)`            | Unmapped circuit unique IDs        | `span_{serial}_unmapped_tab_{circuit_number}_{suffix}`         | `span_abc123_unmapped_tab_32_power`          | Native operand providers            |
| `construct_unmapped_entity_id(...)`            | Unmapped circuit entity IDs        | `sensor.{device_prefix}_unmapped_tab_{tab}_{suffix}`           | `sensor.span_panel_unmapped_tab_32_power`    | Always device prefix for visibility |
| `get_unmapped_circuit_entity_id(...)`          | Unmapped entity ID lookup          | Convenience wrapper around `construct_unmapped_entity_id(...)` |                                              |                                     |

**Device Identifier Behavior:** `_get_device_identifier_for_unique_ids`

- Live entries: use true panel serial number
- Simulator entries: use slugified device name (e.g., config entry title), ensuring no cross-entry collisions

## Synthetic Sensors

The `ha-synthetic-sensors` library uses the top-level sensor key from the YAML file directly as the `unique_id` for the
sensor. However, to ensure this key is globally unique and prevent collisions, the **SPAN integration** constructs this key
_before_ passing it to the library.

The SPAN integration constructs the key by combining the per-entry device identifier (serial for live, slugified device name
for simulator entries) with a descriptive sensor name.

**Unique ID Pattern (Constructed by SPAN Integration):** `span_{identifier}_{sensor_name}`

Examples:

- Panel synthetic: `span_sp3-001_current_power`
- Solar total: `span_sp3-001_solar_total_power`

This constructed key is then used as the `unique_id` in the Home Assistant entity registry, ensuring data continuity for
statistics.

## YAML Generation for Synthetic Sensors

YAML content is generated by the synthetic coordinator and imported into storage:

- `SyntheticSensorCoordinator._construct_complete_yaml_config(...)` builds the YAML document with `global_settings` and
  `sensors` mappings
- Sensor keys in YAML come from `construct_synthetic_unique_id_for_entry(...)`
- Strings are force-quoted to avoid misinterpretation (custom YAML representer)

Key points:

- Global settings include `device_identifier` used by the synthetic layer for device association and entity_id generation
- Backing entity mapping is prepared and registered before sensor creation

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

**Implementation:** Native SPAN HA Integration. Unique ID patterns for existing installations depend on multiple factors
including installation history and migration state. New installations use circuit_id based patterns for consistency and
migrate old patterns with config schema v2.0.

## Synthetic Sensors

The `ha-synthetic-sensors` library uses the top-level sensor key from the YAML file directly as the `unique_id` for the
sensor. However, to ensure this key is globally unique and prevent collisions, the **SPAN integration** is responsible for
constructing this key _before_ it is passed to the library.

The SPAN integration constructs the key by combining the panel's serial number (as a `device_identifier`) with a descriptive
sensor name.

**Unique ID Pattern (Constructed by SPAN Integration):** `span_{serial_number}_{sensor_key}`

This constructed key is then used as the `unique_id` in the Home Assistant entity registry, ensuring data continuity for
statistics.

## Integration-Managed Multi-Tab/240V Synthetics

The SpanPanel integration allows configuration of synthetic sensors that combine two (or more) tabs (different phases) to
produce a 240V measurement—such as summing two 120V legs for power and energy. This is commonly used for solar, but can also
be used for other multi-tab circuits (e.g., 240V appliances).

The unique ID logic for these sensors is now consistent with all other synthetic sensors. The SPAN integration constructs a
globally unique key (e.g., `span_{serial_number}_solar_total_power`), which is then used as the `unique_id` for the entity.
This ensures stability and compatibility for statistics and migration.

### Legacy Solar Sensors (Pre-v1.2.0)

**Legacy Solar Sensor Unique ID Pattern:**

```text
span_{serial_number}_synthetic_{leg1}_{leg2}_{yaml_key}
```

**Migration Behavior:**

Pre v1.2.0 Legacy HA config version is 1.0 Post v1.2.0 HA config version is 2.0

### New Installation

**Unique ID Pattern:** `span_{serial_number}_{circuit_id}_{description_key}`

| Circuit Type        | Unique ID Example                                              | Description                  |
| ------------------- | -------------------------------------------------------------- | ---------------------------- |
| **Named Circuits**  | `span_abc123_0dad2f16cd514812ae1807b0457d473e_power`           | Kitchen outlets on a circuit |
| **Named Circuits**  | `span_abc123_0dad2f16cd514812ae1807b0457d473e_energy_produced` | Solar on a circuit           |
| **Switch Entities** | `span_abc123_0dad2f16cd514812ae1807b0457d473e_relay_1`         | Circuit breaker control      |

A backing entity should follow the same pattern in order to map to the synthetic that is services:
span*{serial_number}*{circuit*id}\_backing*{description_key}

### Unmapped Tab Entities (v1.2.0+)

**Unique ID Pattern:** `span_{serial_number}_unmapped_tab_{tab_number}_{description_key}`

| Circuit Type            | Unique ID Example                                    | Description                                  |
| ----------------------- | ---------------------------------------------------- | -------------------------------------------- |
| **Unmapped Tab Power**  | `span_nj-2316-005k6_unmapped_tab_32_power`           | Unmapped breaker position 32 power           |
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

| Entity Type      | Unique ID Example           | Description                  |
| ---------------- | --------------------------- | ---------------------------- |
| **Panel Power**  | `span_abc123_current_power` | Main panel power             |
| **Panel Status** | `span_abc123_dsm_state`     | Demand side management state |
| **Panel Info**   | `span_abc123_softwarever`   | Panel software version       |
| **Door State**   | `span_abc123_doorstate`     | Panel door open/closed       |

### Synthetic Sensors (v1.2.0+)

**Unique ID Pattern:** `span_{serial_number}_{sensor_key}`

| Sensor Type            | Unique ID Example                    | Description              |
| ---------------------- | ------------------------------------ | ------------------------ |
| **Solar Total**        | `span_abc123_solar_total_power`      | Combined solar power     |
| **Backup Circuits**    | `span_abc123_backup_circuits_power`  | Backup circuit total     |
| **Custom Calculation** | `span_abc123_whole_house_efficiency` | User-defined calculation |

## Sensor Setup Timing and Dependencies

**Timing Requirements:**

The SPAN HA Integration must ensure proper setup of the device and unmapped circuits first order to prevent startup errors
where synthetic sensors reference unavailable entities.

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
