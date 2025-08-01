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
Time 10:02 - Energy Sensor: unavailable
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
- Continue showing last known values
- Resume normal operation when panel reconnects
- Go `unavailable` only after 15 minutes of continuous outage

### Non-Energy Sensors (Immediate Availability)

**Affected Sensors:**

- Power sensors (instantaneous measurements)
- Status sensors (door state, connection status)
- Configuration sensors
- Any sensor without `state_class=TOTAL_INCREASING`

**Behavior During Outages:**

- Go `unavailable` immediately when panel connection is lost
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

### Edge Cases

**Long Outages (>15 minutes):**

- Energy sensors will eventually go `unavailable`
- Statistics integrity preserved for the grace period duration
- Normal unavailable behavior resumes after timeout

**Integration Restart During Outage:**

- Grace period resets (no stored timestamp)
- Sensors go `unavailable` immediately until panel reconnects
- Normal operation resumes on first successful update

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

- **Synthetic Exception Handling**: `UNAVAILABLE` handlers with conditional logic
- **Computed Variables**: `within_grace` variable with independent exception handling
- **Global Variables**: `energy_grace_period_minutes` for runtime configuration
- **DateTime Functions**: `now()` and `state.last_changed` for time calculations
- **Diagnostic Attributes**: `grace_period_active` for monitoring

## Synthetic Sensor Implementation

### Energy Sensor Template Structure

All energy sensors use this standardized structure:

```yaml
sensor_name:
  name: "Sensor Display Name"
  entity_id: "sensor.entity_id"
  formula: "entity_id"
  UNAVAILABLE: "if(within_grace, state, UNAVAILABLE)"
  variables:
    within_grace:
      formula: "((now() - state.last_changed) / 60) < energy_grace_period_minutes"
      UNAVAILABLE: "false"
  attributes:
    grace_period_active:
      formula: "within_grace"
  metadata:
    unit_of_measurement: "Wh"
    device_class: "energy"
    state_class: "total_increasing"
```

### Tab Connected Solar Energy Sensors (Special Handling)

Solar sensors include additional exception handling for unmapped circuits:

```yaml
solar_energy_sensor:
  name: "Solar Produced Energy"
  entity_id: "sensor.solar_energy"
  formula: "leg1_produced + leg2_produced"
  UNAVAILABLE: "if(within_grace, state, UNAVAILABLE)"
  variables:
    leg1_produced: "sensor.circuit_30_energy_produced"
      UNAVAILABLE: "if(within_grace, state, 0)"
    leg2_produced: "sensor.circuit_32_energy_produced"
      UNAVAILABLE: "if(within_grace, state, 0)"
    within_grace:
      formula: "((now() - state.last_changed) / 60) < energy_grace_period_minutes"
      UNAVAILABLE: "false"
  attributes:
    grace_period_active:
      formula: "within_grace"
```

## Grace Period Logic Breakdown

**Normal Operation:**

1. `formula: "entity_id"` - Direct passthrough of backing entity value
2. No exception handling triggered when backing entity is available

**During Panel Outage:**

1. Backing entity becomes unavailable
2. `UNAVAILABLE` handler triggers: `"if(within_grace, state, UNAVAILABLE)"`
3. `within_grace` computed variable evaluates: `"((now() - state.last_changed) / 60) < energy_grace_period_minutes"`
4. If within grace period: returns last known `state` value
5. If beyond grace period: returns `UNAVAILABLE`

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
