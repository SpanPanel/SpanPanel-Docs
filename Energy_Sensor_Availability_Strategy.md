# Energy Sensor Availability Strategy

@sargonas identified this issue and proved the state concept with the grace period, many thanks for extensive anlysis!

## The Problem

Home Assistant's energy dashboard and long-term statistics rely on continuous energy sensor data to calculate energy
consumption deltas. When energy sensors go `unavailable` and then return with values, Home Assistant incorrectly calculates
energy usage from zero instead of from the last known value.

### Example of the Issue

**Without Grace Period:**

```text
Time 10:00 - Energy Sensor: 1000 kWh (available)
Time 10:01 - SPAN Panel offline
Time 10:02 - Energy Sensor: UNKNOWN
Time 10:03 - SPAN Panel back online
Time 10:04 - Energy Sensor: 1002 kWh (available)

Home Assistant calculates: 1002 - 0 = 1002 kWh used in 4 minutes
```

**With Grace Period:**

```text
Time 10:00 - Energy Sensor: 1000 kWh (available)
Time 10:01 - SPAN Panel offline
Time 10:02 - Energy Sensor: 1000 kWh (still showing available with cached value)
Time 10:03 - SPAN Panel back online
Time 10:04 - Energy Sensor: 1002 kWh (available with fresh data)
```

Home Assistant calculates: 1002 - 1000 = 2 kWh used in 4 minutes ✓

## Behavior

### Energy Sensors (15-minute Grace Period)

**Affected Sensors:**

- Circuit Energy Consumed sensors
- Circuit Energy Produced sensors
- Panel Energy Consumed sensors
- Panel Energy Produced sensors
- Any sensor with `state_class=SensorStateClass.TOTAL_INCREASING`

**Behavior During Outages:**

- Remain `available` for up to 15 minutes during panel outages
- Continue showing last known values via `state` token resolution
- Resume normal operation when panel reconnects
- Go `UNKNOWN` only after 15 minutes of continuous outage

### Non-Energy Sensors (Immediate Availability)

**Affected Sensors:**

- Power sensors (instantaneous measurements)
- Status sensors (door state, connection status)
- Configuration sensors
- Any sensor without `state_class=TOTAL_INCREASING`

**Behavior During Outages:**

- Go `UNKNOWN` immediately when panel connection is lost
- Resume normal operation when panel reconnects
- Standard Home Assistant availability behavior

## Configuration

This strategy is **automatically applied** and requires no user configuration. The integration determines which sensors need
grace period availability based on their `state_class` attribute.

## Grace Period Duration

The grace period is defaulted to **15 minutes (900 seconds)**.

## Technical Considerations

### Performance Impact

- Negligible: Simple timestamp comparison during availability checks
- No additional API calls or background processing
- Metadata function evaluation is cached during sensor updates

### Edge Cases

**Long Outages (>15 minutes):**

- Energy sensors will eventually go `UNKNOWN` after grace period expires
- Statistics integrity preserved for the grace period duration
- Normal unavailable behavior resumes after timeout

**Integration Restart During Outage:**

- Grace period resets (no stored timestamp)
- Sensors go `UNKNOWN` immediately until panel reconnects
- Normal operation resumes on first successful update

**Metadata Function Availability:**

- Requires proper mock state setup in tests with `last_changed`, `entity_id`, `object_id`, `domain` attributes
- Framework validation now accepts entity ID references in computed variables
- Self-referential `metadata(state, 'last_changed')` works correctly with `state` token resolution

## Proof of Concept Pre-Synthetic Implementation History

- **Commit**: `935bb46e560ca97b56f72d5f493003b550f5dba3`
- **Date**: June 26, 2025
- **Author**: sargonas
- **Files Modified**:
  - `custom_components/span_panel/coordinator.py` (+22 lines)
  - `custom_components/span_panel/sensor.py` (+11 lines)

## Related Documentation

- [Home Assistant Energy Management](https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics)
- [Sensor State Classes](https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes)
- [DataUpdateCoordinator Best Practices](https://developers.home-assistant.io/docs/integration_fetching_data/)

## Synthetic Dependencies

- **Synthetic Exception Handling**: `UNAVAILABLE` and `UNKNOWN` handlers with conditional logic
- **Computed Variables**: `within_grace` variable with independent exception handling
- **Global Variables**: `energy_grace_period_minutes` for runtime configuration
- **Metadata Functions**: `metadata(state, 'last_changed')` for self-referential timestamp access
- **DateTime Functions**: `now()` and `minutes_between()` for time calculations
- **Diagnostic Attributes**: `grace_period_active` for monitoring
- **State Token Resolution**: Automatic `state` token resolution to backing entity

## Synthetic Sensor Implementation

### Energy Sensor Template Structure

All energy sensors use this standardized structure with the corrected implementation:

```yaml
{{sensor_key}}:
  name: "{{sensor_name}}"
  entity_id: "{{entity_id}}"
  formula: "state"
  UNAVAILABLE: "state if within_grace else UNKNOWN"
  UNKNOWN: "state if within_grace else UNKNOWN"
  variables:
    within_grace:
      formula: "minutes_between(metadata(state, 'last_changed'), now()) < energy_grace_period_minutes"
      UNAVAILABLE: 'false'
      UNKNOWN: 'false'
  attributes:
    tabs: "{{tabs_attribute}}"
    voltage: {{voltage_attribute}}
    grace_period_active:
      formula: "within_grace"
  metadata:
    unit_of_measurement: "Wh"
    device_class: "energy"
    state_class: "total_increasing"
    suggested_display_precision: {{energy_display_precision}}
```

### Solar Energy Sensors (Special Handling)

Solar sensors include additional exception handling for leg components:

```yaml
{{sensor_key}}:
  name: "Solar Consumed Energy"
  entity_id: "{{entity_id}}"
  formula: "leg1_consumed + leg2_consumed"
  UNAVAILABLE: "state if within_grace else UNKNOWN"
  UNKNOWN: "state if within_grace else UNKNOWN"
  variables:
    leg1_consumed: 
      formula: "{{leg1_consumed_entity}}"
      UNAVAILABLE: "leg1_consumed if within_grace else 0"
    leg2_consumed: 
      formula: "{{leg2_consumed_entity}}"
      UNAVAILABLE: "leg2_consumed if within_grace else 0"
    within_grace:
      formula: "minutes_between(metadata(state, 'last_changed'), now()) < energy_grace_period_minutes"
      UNAVAILABLE: 'false'
      UNKNOWN: 'false'
  attributes:
    tabs: "{{tabs_attribute}}"
    voltage: {{voltage_attribute}}
    grace_period_active:
      formula: "within_grace"
  metadata:
    unit_of_measurement: "Wh"
    device_class: "energy"
    state_class: "total_increasing"
    suggested_display_precision: {{energy_display_precision}}
```

## Grace Period Logic Breakdown

**Normal Operation:**

1. `formula: "state"` - Direct passthrough of backing entity value via `state` token
2. No exception handling triggered when backing entity is available
3. `within_grace` computed variable evaluates to `false` (no outage detected)

**During Panel Outage:**

1. Backing entity becomes unavailable
2. `UNAVAILABLE` handler triggers: `"state if within_grace else UNKNOWN"`
3. `within_grace` computed variable evaluates:
   `"minutes_between(metadata(state, 'last_changed'), now()) < energy_grace_period_minutes"`
4. If within grace period: returns last known `state` value
5. If beyond grace period: returns `UNKNOWN`

**Key Implementation Details:**

- Uses `metadata(state, 'last_changed')` for self-referential timestamp access
- `state` token automatically resolves to the sensor's backing entity
- Both `UNAVAILABLE` and `UNKNOWN` handlers use the same grace period logic
- `grace_period_active` attribute provides diagnostic visibility

## Configuration Integration

### Global Variable Configuration

The header template includes the configurable grace period:

```yaml
version: "1.0"

global_settings:
  device_identifier: "{{device_identifier}}"
  variables:
    energy_grace_period_minutes: "{{energy_grace_period_minutes}}"
  metadata:
    attribution: "Data from SPAN Panel"

sensors:
```

### User Configuration Options

**Location**: Configuration → Integrations → SPAN Panel → Configure → General Options

**Field**: "Energy Sensor Grace Period (minutes)"

**Settings**:

- **Range**: 0-60 minutes
- **Default**: 15 minutes
- **Validation**: Integer values only
- **Description**: "How long energy sensors maintain their last known value when the panel becomes unavailable (0-60
  minutes). Helps preserve energy statistics integrity during brief outages."

```

```
