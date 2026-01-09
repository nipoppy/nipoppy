# Nipoppy Telemetry Server

SERVER-SIDE observability stack for collecting and visualizing Nipoppy metrics.

## Architecture

```
┌──────────────┐      OTLP/gRPC      ┌─────────────────┐
│  Nipoppy CLI │ ──────────────────► │ OTel Collector  │
│  (CLIENT)    │    port 4317        │    (SERVER)     │
└──────────────┘                     └────────┬────────┘
                                              │
                                   Prometheus Exporter
                                        port 8889
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │   Prometheus    │
                                     │    (SERVER)     │
                                     └────────┬────────┘
                                              │
                                        PromQL queries
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │     Grafana     │
                                     │    (SERVER)     │
                                     │   port 3000     │
                                     └─────────────────┘
```

## Quick Start

### 1. Start the Server Stack

```bash
cd server
docker-compose up -d
```

### 2. Verify Services

```bash
docker-compose ps
```

All three services should show "Up" status:
- `nipoppy-otel-collector`
- `nipoppy-prometheus`
- `nipoppy-grafana`

### 3. Access Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

### 4. Configure Client

Set environment variable on client machines:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
```

Or for remote server:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=your-server.example.com:4317
```

### 5. Run Nipoppy Commands

```bash
nipoppy init /tmp/test-dataset
```

Metrics will appear in Grafana within ~5 seconds.

## Metrics Collected

### 1. Command Execution (Core Feature)
- **Name**: `nipoppy_commands_executed_total`
- **Type**: Counter
- **Labels**: `command` (init, bidsify, process, etc.)
- **Purpose**: Track which commands are used and how often

### 2. Geographic Distribution (Additional Feature)
- **Name**: `nipoppy_location_by_country`
- **Type**: Gauge
- **Labels**: `country` (ISO country code)
- **Purpose**: Track where installations are located

## Configuration

### Demo Settings (Current)

Optimized for live presentations with ~5 second latency:

| Component | Setting | Value |
|-----------|---------|-------|
| CLI export interval | `export_interval_millis` | 1000ms (1s) |
| Collector batch timeout | `timeout` | 500ms |
| Collector batch size | `send_batch_size` | 10 |
| Prometheus scrape | `scrape_interval` | 5s |
| Grafana refresh | `refresh` | 5s |

**Total latency**: ~5-6 seconds from command to dashboard

### Production Settings

For production deployments, update the following:

**1. Client (`nipoppy/telemetry/metrics.py`)**:
```python
initialize_telemetry(
    export_interval_millis=10000,  # 10 seconds
)
```

**2. Collector (`configs/otel-collector-config.yaml`)**:
```yaml
processors:
  batch:
    timeout: 5s          # Uncomment production settings
    send_batch_size: 100
```

**3. Prometheus (`configs/prometheus.yml`)**:
```yaml
global:
  scrape_interval: 15s   # Uncomment production settings
```

## Directory Structure

```
server/
├── docker-compose.yml         # Service orchestration
├── .env.example              # Environment variables template
├── README.md                 # This file
└── configs/
    ├── otel-collector-config.yaml   # Collector pipeline config
    ├── prometheus.yml               # Prometheus scrape config
    └── grafana/
        ├── datasources.yaml         # Prometheus datasource
        └── dashboards/
            ├── dashboards.yaml      # Dashboard provisioning
            ├── nipoppy-telemetry.json   # Main dashboard (NEW)
            └── nipoppy-init.json        # Legacy dashboard
```

## Dashboard Panels

### Section 1: Command Usage

1. **Total Commands Executed** (Stat)
   - Query: `sum(nipoppy_commands_executed_total)`
   - Shows cumulative command count

2. **Commands Over Time** (Time series)
   - Query: `sum by (command) (rate(nipoppy_commands_executed_total[5m]))`
   - Shows command frequency trends

3. **Command Distribution** (Pie chart)
   - Query: `topk(10, sum by (command) (nipoppy_commands_executed_total))`
   - Shows which commands are most popular

### Section 2: Geographic Distribution

4. **Total Countries** (Stat)
   - Query: `count(nipoppy_location_by_country)`
   - Shows number of unique countries

5. **Top Countries by Installations** (Table)
   - Query: `topk(10, sum by (country) (nipoppy_location_by_country))`
   - Ranked list of countries

6. **Country Distribution** (Pie chart)
   - Query: `topk(10, sum by (country) (nipoppy_location_by_country))`
   - Percentage breakdown by country

## Troubleshooting

### Metrics Not Appearing?

**1. Check collector logs:**
```bash
docker-compose logs otel-collector
```

Look for errors or "Exporting metrics" messages.

**2. Check collector endpoint:**
```bash
curl http://localhost:8889/metrics | grep nipoppy
```

Should show `nipoppy_*` metrics.

**3. Check Prometheus targets:**

Open http://localhost:9090/targets

The `otel-collector` target should be "UP".

**4. Check Prometheus metrics:**
```bash
curl http://localhost:9090/api/v1/label/__name__/values | grep nipoppy
```

Should list `nipoppy_commands_executed_total` and `nipoppy_location_by_country`.

### Dashboard Showing "No Data"?

1. **Wait 10 seconds** for initial scrape
2. **Check time range**: Default is "Last 15 minutes"
3. **Run a nipoppy command** to generate metrics:
   ```bash
   nipoppy init /tmp/test
   ```
4. **Check query in Explore**: http://localhost:9090/graph

### Collector Not Starting?

Check configuration syntax:
```bash
docker-compose config
```

Check port conflicts:
```bash
netstat -an | grep -E '4317|8889|9090|3000'
```

## Production Deployment

### Security Checklist

- [ ] Enable TLS for OTLP endpoint
  - Update `insecure: true` in `otel-collector-config.yaml`

- [ ] Set strong Grafana password
  - Change `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml`

- [ ] Configure firewall rules
  - Allow: 4317 (OTLP), 3000 (Grafana)
  - Block: 8889 (collector metrics), 9090 (Prometheus)

- [ ] Set up authentication for Prometheus
  - Add basic auth or use reverse proxy

- [ ] Enable HTTPS for Grafana
  - Use reverse proxy (nginx, traefik) or Grafana TLS config

- [ ] Review data retention policies
  - Prometheus: `--storage.tsdb.retention.time`
  - Collector: `metric_expiration`

### Scaling

For high-traffic deployments:

**1. Add collector replicas:**
```yaml
otel-collector:
  deploy:
    replicas: 3
```

Add load balancer (HAProxy, nginx) in front.

**2. Configure Prometheus remote write:**
```yaml
remote_write:
  - url: "https://your-remote-storage.example.com/write"
```

**3. Use Grafana Cloud or hosted solution**

**4. Implement metric aggregation:**
```yaml
processors:
  cumulativetodelta:
    include:
      match_type: strict
      metrics: ["nipoppy.commands.executed"]
```

## Monitoring the Monitor

### Collector Metrics

Collector exposes its own metrics on port 8888:
```bash
curl http://localhost:8888/metrics
```

Key metrics:
- `otelcol_receiver_accepted_metric_points`
- `otelcol_exporter_sent_metric_points`
- `otelcol_processor_batch_batch_send_size_bucket`

### Prometheus Metrics

```bash
curl http://localhost:9090/metrics
```

Key metrics:
- `prometheus_tsdb_head_samples`
- `prometheus_tsdb_compaction_duration_seconds`

## Backup and Recovery

### Backup Prometheus Data

```bash
docker-compose stop prometheus
tar czf prometheus-backup-$(date +%Y%m%d).tar.gz \
  -C /var/lib/docker/volumes/ prometheus-data
docker-compose start prometheus
```

### Backup Grafana Dashboards

```bash
docker-compose stop grafana
tar czf grafana-backup-$(date +%Y%m%d).tar.gz \
  -C /var/lib/docker/volumes/ grafana-data
docker-compose start grafana
```

Or export dashboards via API:
```bash
curl -u admin:admin http://localhost:3000/api/dashboards/uid/nipoppy-telemetry \
  > dashboard-backup.json
```

## Logs

### View logs for all services:
```bash
docker-compose logs -f
```

### View logs for specific service:
```bash
docker-compose logs -f otel-collector
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

## Stopping the Stack

### Stop services (preserve data):
```bash
docker-compose stop
```

### Stop and remove containers (preserve volumes):
```bash
docker-compose down
```

### Remove everything including data:
```bash
docker-compose down -v
```

## Performance Tuning

### Collector

```yaml
processors:
  memory_limiter:
    limit_mib: 512      # Increase for high traffic
    spike_limit_mib: 128

  batch:
    timeout: 5s
    send_batch_size: 1000  # Larger batches for efficiency
```

### Prometheus

```yaml
storage:
  tsdb:
    retention.time: 30d      # Adjust retention
    retention.size: 10GB     # Limit storage size
```

## Further Reading

- [OpenTelemetry Collector Documentation](https://opentelemetry.io/docs/collector/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
