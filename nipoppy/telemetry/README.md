# Nipoppy Telemetry

CLIENT-SIDE instrumentation for tracking command usage and geographic distribution.

## Architecture

```
nipoppy CLI (DELTA=1/run)
  └─► OTel Collector :4317
        └─► deltatocumulative processor  (accumulates 1+1+1 → cumulative 3)
              └─► Prometheus exporter :8889
                    └─► Prometheus → Grafana
```

### Why deltatocumulative?

Each `nipoppy` run is a short-lived process. Its counter starts at 0 and adds 1 before
the process exits — so each run sends `DELTA = 1`. Without accumulation the collector
would forward that raw `1` to Prometheus every time and `sum()` would always return `1`.

The `deltatocumulative` processor keeps a running total in memory:
run 1 → 1, run 2 → 2, run 3 → 3. Prometheus then scrapes the growing cumulative value
and `sum()` returns the correct all-time total.

See: https://oneuptime.com/blog/post/2026-02-06-delta-to-cumulative-processor-opentelemetry-collector/view

---

## What Gets Tracked

| Metric | Type | Recorded when |
|--------|------|---------------|
| `nipoppy_commands_executed_total{command}` | Counter | Any command starts |
| `nipoppy_commands_completed_total{command, status, return_code}` | Counter | Any command exits |
| `nipoppy_location_by_country_installations_total{country}` | Counter | `nipoppy init` only |

`status` is one of `success`, `partial`, or `failure`.  
`country` is a two-letter ISO code (e.g. `CA`, `US`) resolved via GeoIP on `nipoppy init`.

---

## Module Structure

```
nipoppy/telemetry/
├── __init__.py       # Public API exports
├── decorators.py     # @track_command decorator
├── metrics.py        # OTel provider setup and metric instruments
├── geo.py            # GeoIP location lookup (nipoppy init only)
└── README.md         # This file
```

---

## Usage

### Any command

```python
from nipoppy.telemetry import track_command

@track_command("bidsify")
def bidsify(**params):
    ...
```

### Init command (also records location)

```python
from nipoppy.telemetry import track_command
from nipoppy.telemetry.geo import record_location

@track_command("init")
def init(**params):
    workflow.run()
    record_location()   # one-time GeoIP lookup, recorded as a metric
```

---

## Key Design Principles

### 1. Fail-safe

All telemetry is wrapped in try-except. Commands always execute even if telemetry fails.

### 2. DELTA temporality forced in code

`metrics.py` sets `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=delta` before
creating the exporter. Without this the `OTLPMetricExporter` defaults to CUMULATIVE,
sending `value=1` on every run with no accumulation across process runs.

### 3. Minimal footprint

CLI integration is one decorator per command and a single `initialize_telemetry()` call
at startup.

---

## Configuration

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | Collector address |
| `OTEL_SDK_DISABLED` | `false` | Set to `true` to disable all telemetry |
| `ENVIRONMENT` | `development` | Tag applied to all metrics |

### Pointing to the shared server

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://206.12.94.146:4317
```

Add to `~/.zshrc` or `~/.bashrc` to make it permanent.

### Opting out

```bash
export OTEL_SDK_DISABLED=true
```

---

## GeoIP Lookup

**When**: once during `nipoppy init`, never on subsequent commands.  
**How**:
1. Fetches public IP from `https://api.ipify.org`
2. Resolves country via `https://api.db-ip.com/v2/free/{ip}` (free tier, 1,000 req/day)
3. Records `country` attribute on the `nipoppy_location_by_country_installations_total` metric

Falls back to `country="UNKNOWN"` on any failure (timeout, rate limit, no network).

---

## Troubleshooting

**Counter stuck at 1**
- Confirm `OTEL_EXPORTER_OTLP_ENDPOINT` includes the `http://` scheme
- Confirm the collector has `deltatocumulative` in its processor pipeline

**Telemetry disabled unintentionally**
```bash
echo $OTEL_SDK_DISABLED   # should be empty or "false"
```

**GeoIP returns UNKNOWN**
- No network access, or db-ip.com free-tier rate limit hit (shared egress IP on HPC)
- Commands still run normally — location just records as `UNKNOWN`

---

## Further Reading

- [deltatocumulative processor](https://oneuptime.com/blog/post/2026-02-06-delta-to-cumulative-processor-opentelemetry-collector/view)
- [OpenTelemetry Metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/)
- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/)
