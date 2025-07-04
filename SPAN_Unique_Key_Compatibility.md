# SPAN Unique Key Compatibility

Without unique key compatibility an upgrade will create new sensors or will create sensors with '_2' suffix
since the entity id will match but the unique ID will not. This behavior will result in lost statistics
as the new sensor will not match the old sensor with the existing history. The integration has tests
to specifically ensure compatibility from one release to the next.

**Unique IDs vs Entity IDs:**

- **Unique IDs**: Provide statistics continuity, must be migrated and preserved during upgrades
- **Entity IDs**: Primary reference for user templates and UI; Can change based on version and user configuration flags, maybe renamed by user.

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

## Integration Manaaged Solar Synthetics

The SpanPanel integration has an option configuration to define two legs (different phases) in order
two produce one 240V circuit where the two 120V legs are added together for both power and energy.  This configuration
is a conviencce where solar is wired into two tabs like tab 30/32 which is done in some installations where a non-SPAN
inverter is used between the inverter and the panel.  The unique keys in these configuration has changed to become
consistent with standard synthetic unique ID's

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
