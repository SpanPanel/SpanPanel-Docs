# AST Formula Compilation Example

This document illustrates how the synthetic sensors package converts formula strings into executable form using Abstract Syntax Tree (AST) parsing.

The synthetic sensors package uses AST parsing to safely convert formula strings into cached, executable functions.
This technique provides both security (no dangerous `eval()`) and performance (compiled formulas are cached and reused).

## Formula Transformation Process

### Step 1: Input Formula String

```yaml
formula: "solar_power / max_capacity * 100 if max_capacity > 0 else 0"
variables:
  solar_power: "sensor.solar_inverter_power"
  max_capacity: "input_number.solar_max_capacity"
```

### Step 2: AST Representation (Parsed Structure)

The formula gets broken down into a structured tree:

```python
ConditionalExpression(
    # The condition: max_capacity > 0
    test=Compare(
        left=Name(id='max_capacity'),           # Variable reference: max_capacity
        ops=[Gt()],                             # Operator: >
        comparators=[Constant(value=0)]         # Constant: 0
    ),
    
    # If condition is true: solar_power / max_capacity * 100
    body=BinOp(
        left=BinOp(
            left=Name(id='solar_power'),        # Variable: solar_power
            op=Div(),                           # Operator: /
            right=Name(id='max_capacity')       # Variable: max_capacity
        ),
        op=Mult(),                              # Operator: *
        right=Constant(value=100)               # Constant: 100
    ),
    
    # If condition is false: 0
    orelse=Constant(value=0)
)
```

### Step 3: Cached Executable Form

The AST is compiled into a function-like object that can be executed efficiently:

```python
# Conceptually equivalent to this compiled function:
def cached_formula_solar_efficiency(solar_power, max_capacity):
    if max_capacity > 0:
        return (solar_power / max_capacity) * 100
    else:
        return 0
```

## Before and After Comparison

### WITHOUT Cache (Every Evaluation)

```python
# Every sensor update requires:
formula_string = "solar_power / max_capacity * 100 if max_capacity > 0 else 0"

# 1. Parse the string into tokens
tokens = tokenize(formula_string)  # ~1ms

# 2. Build Abstract Syntax Tree
ast_tree = parse_tokens(tokens)    # ~2ms

# 3. Validate syntax and safety
validate_ast(ast_tree)             # ~1ms

# 4. Extract variable dependencies
dependencies = extract_deps(ast_tree)  # ~1ms

# 5. Fetch current entity states
solar_power = hass.states.get("sensor.solar_inverter_power").state  # ~0.5ms
max_capacity = hass.states.get("input_number.solar_max_capacity").state  # ~0.5ms

# 6. Execute the calculation
result = execute_ast(ast_tree, {"solar_power": solar_power, "max_capacity": max_capacity})  # ~0.5ms

# Total: ~6.5ms per evaluation
```

### WITH Cache (After First Evaluation)

```python
# First evaluation: Parse + Compile + Cache
compiled_formula = cache.get_or_create("solar_efficiency_formula")  # One-time ~6ms

# Subsequent evaluations:
# 1. Get cached compiled formula
compiled_formula = cache.get("solar_efficiency_formula")  # ~0.1ms

# 2. Fetch current entity states (always fresh)
solar_power = hass.states.get("sensor.solar_inverter_power").state  # ~0.5ms
max_capacity = hass.states.get("input_number.solar_max_capacity").state  # ~0.5ms

# 3. Execute the cached formula
result = compiled_formula.execute({"solar_power": solar_power, "max_capacity": max_capacity})  # ~0.1ms

# Total: ~1.2ms per evaluation (5x faster)
```

## Safety Features

### Dangerous Operations Blocked

The AST parser prevents dangerous operations:

```python
# These would be BLOCKED by AST validation:
"__import__('os').system('rm -rf /')"     # Import statements
"exec('malicious code')"                  # Code execution
"open('/etc/passwd').read()"              # File access
"globals()['secret_key']"                 # Global access
```

### Safe Operations Allowed

```python
# These are ALLOWED by AST validation:
"solar_power + grid_power"                # Basic arithmetic
"max(temp1, temp2, temp3)"                # Math functions  
"value if condition else 0"               # Conditional expressions
"sqrt(power_a**2 + power_b**2)"          # Mathematical operations
```

## Real-World Performance Impact

For a typical SPAN panel integration with 20 synthetic sensors updating every 10 seconds:

### Without Cache

- 20 sensors × 6.5ms = 130ms per update cycle

### With Cache

- 20 sensors × 1.2ms = 24ms per update cycle
- **5x performance improvement**

## Cache Invalidation

The cache is cleared only when the formula itself changes:

```python
# Cache cleared when:
- Formula string changes: "A + B" → "A * B"
- Variable mappings change: solar_power: sensor.old → sensor.new  
- force_update_formula() called
- Configuration reload occurs

# Cache NOT cleared when:
- Entity states change: sensor.solar_power: 1500W → 1600W
- Normal sensor updates occur
- Dependencies trigger updates
```
