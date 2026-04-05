# Nipoppy Telemetry

CLIENT-SIDE instrumentation for tracking command usage and geographic distribution.

## Architecture: Separation of Concerns

This telemetry system tracks **two independent features**:

### 1. Command Tracking (Core Feature)
- **Metric**: `nipoppy.commands.executed` (Counter)
- **Attributes**: `command` (e.g., "init", "bidsify", "process")
- **Purpose**: Track which commands are used and how often
- **Implementation**: `@track_command` decorator

### 2. Location Tracking (Additional Feature)
- **Metric**: `nipoppy.location.by_country` (Gauge)
- **Attributes**: `country` (ISO country code: "US", "CA", etc.)
- **Purpose**: Track geographic distribution of installations
- **Implementation**: Separate functions in `geo.py`

**Why Separate?**
- **Modularity**: Enable/disable features independently
- **Clarity**: Each metric has a single, clear purpose
- **Privacy**: Users can opt out of location while keeping command stats
- **Presentation**: Easy to explain "we track commands AND locations"

## Module Structure

```
nipoppy/telemetry/
├── __init__.py       # Public API exports
├── decorators.py     # @track_command decorator
├── metrics.py        # Metric definitions and OpenTelemetry setup
├── geo.py            # GeoIP location tracking
└── README.md         # This file
```

## Usage

### Basic Usage (Commands)

```python
from nipoppy.telemetry import track_command, initialize_telemetry

# Initialize once at startup
initialize_telemetry()

# Decorate commands
@track_command("bidsify")
def bidsify(**params):
    # Command logic here
    ...
```

### Init Command (Command + Location)

```python
from nipoppy.telemetry import (
    track_command,
    save_country_to_config,
    record_location,
)

@track_command("init")
def init(**params):
    # Initialize dataset
    workflow.run()

    # Save location and record metric (separate from command)
    save_country_to_config(params)  # One-time GeoIP lookup
    record_location(params)         # Record location metric
```

## Key Design Principles

### 1. Fail-Safe
All telemetry operations are wrapped in try-except blocks. Commands **always execute**, even if telemetry fails.

```python
def _record_command_metric(command_name: str):
    try:
        metrics = get_metrics()
        if metrics:
            metrics["commands_executed"].add(1, {"command": command_name})
    except Exception:
        pass  # Silent failure - never crash user's command
```

### 2. Optional Dependencies
Telemetry gracefully handles missing dependencies:

```python
try:
    from nipoppy.telemetry import track_command
    _TELEMETRY_AVAILABLE = True
except ImportError:
    _TELEMETRY_AVAILABLE = False
    def track_command(name):
        return lambda f: f  # No-op decorator
```

### 3. Minimal Footprint
CLI integration requires only:
- Import statements (~5 lines)
- Initialization call (~3 lines)
- One decorator per command (~1 line each)

**Total**: ~30 lines of telemetry code in `cli.py` (down from ~340 in previous designs)

## Metrics Details

### Metric 1: Command Execution

```python
name: "nipoppy.commands.executed"
type: Counter
unit: "commands"
attributes:
  - command: str  # e.g., "init", "bidsify", "process"

# Example data
nipoppy_commands_executed_total{command="init"} 45
nipoppy_commands_executed_total{command="bidsify"} 32
```

### Metric 2: Location Distribution

```python
name: "nipoppy.location.by_country"
type: UpDownCounter (gauge-like)
unit: "installations"
attributes:
  - country: str  # ISO 3166-1 alpha-2 (e.g., "US", "CA")

# Example data
nipoppy_location_by_country{country="US"} 12
nipoppy_location_by_country{country="CA"} 8
```

## Configuration

### Environment Variables

- `OTEL_EXPORTER_OTLP_ENDPOINT`: Collector address (default: `localhost:4317`)
- `OTEL_SDK_DISABLED`: Set to `"true"` to disable telemetry
- `ENVIRONMENT`: Deployment environment tag (default: `"development"`)
- `GEOIP_DB_PATH`: Path to MaxMind GeoLite2 database (optional)

#### Pointing to the Nipoppy telemetry server

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=206.12.94.146:4317
```

Add this to your `~/.zshrc` or `~/.bashrc` to make it permanent. Once set, all `nipoppy` commands will send telemetry to the central server automatically.

### Dataset Config

Telemetry preferences stored in `global_config.json`:

```json
{
  "CUSTOM": {
    "TELEMETRY": {
      "SEND_TELEMETRY": true,
      "COUNTRY_CODE": "US"
    }
  }
}
```

## GeoIP Lookup

**When**: Called **once** during `nipoppy init`
**How**:
1. Fetches public IP from `https://api.ipify.org`
2. Looks up country in MaxMind GeoLite2-Country database
3. Stores result in dataset config

**Subsequent commands**: Read country from config (no repeated API calls)

## Presentation Guide

### Demo Flow (5 minutes)

1. **Show empty dashboard**
   - Open Grafana: http://localhost:3000

2. **Run init command**
   ```bash
   nipoppy init /tmp/demo1
   ```
   - Watch "Total Commands" increment (~5 seconds)
   - See country appear in location table

3. **Run other commands**
   ```bash
   nipoppy bidsify --dataset /tmp/demo1
   nipoppy process --dataset /tmp/demo1
   ```
   - Watch command breakdown chart update

4. **Explain separation**
   - Point to Section 1: Command Usage (core)
   - Point to Section 2: Geographic Distribution (additional)

### Key Files to Show

1. **`decorators.py`** (~30 lines)
   - Show `@track_command` decorator
   - Highlight fail-safe design

2. **`metrics.py`** (~10 lines of metric definitions)
   - Show two separate metrics
   - Explain separation of concerns

3. **`cli.py`** (~1 line per command)
   - Show decorator usage: `@track_command("bidsify")`
   - Emphasize minimal footprint

## Troubleshooting

### Telemetry not working

1. Check if telemetry is disabled:
   ```bash
   echo $OTEL_SDK_DISABLED  # Should be empty or "false"
   ```

2. Check if collector is running:
   ```bash
   cd server && docker-compose ps
   ```

3. Check CLI startup message:
   ```
   ✓ Telemetry enabled → localhost:4317
   ```

### GeoIP lookup fails

- Country defaults to "UNKNOWN"
- Check `GEOIP_DB_PATH` environment variable
- Download GeoLite2-Country database from MaxMind
- Commands still work normally (fail-safe)

## Production Deployment

### Security Checklist

- [ ] Enable TLS for OTLP endpoint (change `insecure: true`)
- [ ] Set strong collector authentication
- [ ] Review data retention policies
- [ ] Consider privacy regulations (GDPR, etc.)

### Performance Settings

Change in `metrics.py`:
```python
initialize_telemetry(
    export_interval_millis=10000,  # 10 seconds (was 1s for demo)
)
```

Change in `server/configs/`:
- Collector batch timeout: 5s (was 500ms)
- Prometheus scrape: 15s (was 5s)

## Further Reading

- [OpenTelemetry Metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/)
- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
