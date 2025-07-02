# SPAN Unique Key Compatibility

Without unique key compatibility an upgrade will create new sensors or will create sensors with '_2' suffix
since the entity id will match but the unique ID will not. This behavior will result in lost statistics
as the new sensor will not match the old sensor with the existing history. The integration has tests
to specifically ensure compatibility from one release to the next.


**Key Insight - Unique IDs vs Entity IDs:**

- **Unique IDs**: Provide statistics continuity, must be migrated and preserved during upgrades
- **Entity IDs**: Can change based on version and user configuration flags

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

## Solar Synthetics

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

| Sensor Type | Unique ID Example | Description |
|-------------|-------------------|-------------|
| **Instant Power** | `span_abc123_synthetic_15_16_solar_inverter_instant_power` | Solar inverter power |
| **Energy Produced** | `span_abc123_synthetic_15_16_solar_inverter_energy_produced` | Solar energy produced |
| **Energy Consumed** | `span_abc123_synthetic_15_16_solar_inverter_energy_consumed` | Solar energy consumed |
| **Energy Consumed** | `span_nj-2316-005k6_synthetic_30_32_solar_inverter_energy_consumed` | Solar energy consumed (real example) |

**Migration Behavior:**

- **Status**: **MIGRATED** during upgrade to v1.2.0+ (unique_id updated)
- **Statistics**: **PRESERVED** through entity registry unique_id migration
- **Pattern**: Updated to use simplified `span_{serial}_{sensor_key}` format

### Current Solar Sensors (v1.2.0+)

**New Solar Sensor Unique ID Pattern:**

```text
span_{serial_number}_{sensor_key}
```

**Examples:**

- `span_abc123_solar_inverter_power`
- `span_abc123_solar_inverter_energy_produced`
- `span_abc123_solar_inverter_energy_consumed`

**Implementation:**

- **Unique ID migration**: Legacy solar sensors have their unique_ids updated in entity registry
- **Statistics preserved**: Historical data maintained through migration
- **Simplified pattern**: No "synthetic" designation in unique_id
- **Consistent naming**: Matches all other synthetic sensor patterns

## Migration Strategy

### Upgrade from Pre-Synthetic Storage to Synthetic Usage (v1.2.0+)

**SPAN HA Integration Migration Approach:**

**Unique ID Migration:**

1. **Query for existing synthetics**: Search entity registry for unique_ids containing "synthetic"
2. **Extract sensor keys**: Parse `span_{serial}_synthetic_{leg1}_{leg2}_{yaml_key}` to get `yaml_key`
3. **Migrate unique_ids**: Update existing sensors to use simplified `span_{serial}_{sensor_key}` pattern
4. **Preserve statistics**: Entity statistics and history are maintained through unique_id migration
5. **Create new unmapped tabs**: Add unmapped tab native sensors for synthetic sensor dependencies

**Migration Behavior:**

- **Legacy solar sensors**: `span_abc123_synthetic_15_16_solar_inverter_instant_power` → **MIGRATED TO** → `span_abc123_solar_inverter_power`
- **Statistics preserved**: Historical data maintained through entity registry unique_id update
- **Unmapped tabs**: `span_abc123_unmapped_tab_32_instantPowerW` → **CREATED** (new native sensors)

**Rationale:**

- **Statistics preservation**: Users keep their historical synthetic sensor data
- **Simplified pattern**: Future sensors use clean `span_{serial}_{sensor_key}` format
- **Backward compatibility**: Existing installations continue working seamlessly

### Fresh Installation

**New Installation Behavior:**

- All synthetic sensors use simplified pattern: `span_{serial}_{sensor_key}`
- No legacy "synthetic" patterns created
- Consistent with unified naming approach
- Clean unique_id structure from start

## Key Differences

| Aspect | Regular Circuits | Unmapped Tabs | Legacy Solar Sensors | Current Synthetic Sensors |
|--------|------------------|---------------|---------------------|---------------------------|
| **Handler** | SPAN HA Integration (native) | SPAN HA Integration (native) | ha-synthetic-sensors | ha-synthetic-sensors |
| **Unique ID Pattern** | `span_{serial}_{circuit_id}_{desc_key}` | `span_{serial}_unmapped_tab_{num}_{desc_key}` | `span_{serial}_synthetic_{leg1}_{leg2}_{yaml_key}` | `span_{serial}_{sensor_key}` |
| **Generation** | Individual entities | Individual entities | Auto-generated (legacy) | User/Integration defined |
| **Naming** | Circuit-id based | Unmapped tab based | Legacy synthetic pattern | Simplified sensor key |
| **Visibility** | User visible | Hidden from UI | User visible | User visible |
| **Purpose** | Normal circuit monitoring | Synthetic sensor inputs | Solar calculations | General calculations |
| **Setup Timing** | Standard | Before synthetics | After native sensors | After native sensors |
| **Multi-Panel** | Serial in unique ID | Serial in unique ID | Serial in unique ID | Serial in unique ID |
| **Compatibility** | Stable across versions | Never deployed in prod | Migrated during upgrade | v1.0.10+ simplified naming |

## Existing Installation Unique Key Patterns

The following patterns are used by existing installations and can be found in the Home Assistant entity registry:

### Regular Circuit Entities (All Versions)

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
- **Purpose**: Provide stable entity IDs for synthetic sensor calculations like solar or user define synthetics
- **Setup Timing**: Created and added to HA **before** synthetic sensors to ensure proper dependency order

### Panel-Level Entities (All Versions)

Panel level circuits are provided directly by the integration and are not themselves synthetics

**Unique ID Pattern:** `span_{serial_number}_{panel_key}`

| Entity Type | Unique ID Example | Description |
|-------------|-------------------|-------------|
| **Panel Power** | `span_abc123_current_power` | Main panel power |
| **Panel Status** | `span_abc123_dsm_state` | Demand side management state |
| **Panel Info** | `span_abc123_softwarever` | Panel software version |
| **Door State** | `span_abc123_doorstate` | Panel door open/closed |

**Special Characteristics:**

- **Naming Stability**: Never subject to entity ID naming pattern changes

### Legacy Solar Synthetic Sensors (v1.2.0+)

**Unique ID Pattern:** `span_{serial_number}_synthetic_{leg1}_{leg2}_{yaml_key}`

| Sensor Type | Unique ID Example | Description |
|-------------|-------------------|-------------|
| **Instant Power** | `span_abc123_synthetic_15_16_solar_inverter_instant_power` | Solar inverter power |
| **Energy Produced** | `span_abc123_synthetic_15_16_solar_inverter_energy_produced` | Solar energy produced |
| **Energy Consumed** | `span_abc123_synthetic_15_16_solar_inverter_energy_consumed` | Solar energy consumed |

**Implementation Details:**

- **Provided by**: ha-synthetic-sensors package (legacy)
- **Source Data**: Used unmapped tab entities as calculation inputs
- **Migration Status**: **MIGRATED** during upgrade to v1.2.0+ (unique_id updated)
- **Statistics**: **PRESERVED** through entity registry unique_id migration
- **New Pattern**: Updated to use simplified `span_{serial}_{sensor_key}` unique_id pattern

### Current Synthetic Sensors (v2.0+)

**Unique ID Pattern:** `span_{serial_number}_{sensor_key}`

| Sensor Type | Unique ID Example | Description |
|-------------|-------------------|-------------|
| **Solar Total** | `span_abc123_solar_total_power` | Combined solar power |
| **Backup Circuits** | `span_abc123_backup_circuits_power` | Backup circuit total |
| **Custom Calculation** | `span_abc123_whole_house_efficiency` | User-defined calculation |

**Implementation Details:**

- **Provided by**: ha-synthetic-sensors package with SPAN HA Integration configuration
- **Pattern**: Simplified, no "synthetic" designation
- **Flexibility**: SPAN HA Integration defines sensor keys based on functionality
- **Consistency**: Matches simplified naming approach across all sensor types

## Sensor Setup Timing and Dependencies

**Critical Timing Requirements:**

The SPAN HA Integration must ensure proper setup of the device and unmapped circuits first order to prevent startup
errors where synthetic sensors reference unavailable entities.

**Setup Sequence (v2.1.0+):**

1. **Device First**: The device must be configured first so that synthetics can look up the device name as sensor prefix
2. **Native Sensors First**: Create all native sensors (panel-level, unmapped tabs, hardware status) that could be used in synthetic references
3. **Add to Home Assistant**: Call `async_add_entities(entities)` to register native sensors
4. **Synthetic Sensors Last**: Set up synthetic sensors that depend on the now-available device and native sensors

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
