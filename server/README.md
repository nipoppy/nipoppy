# Nipoppy Telemetry — Running Guide

Quick reference for running the telemetry stack locally or against the shared server.

---

## Prerequisites

- Python ≥ 3.10 (any environment — conda, venv, or system Python)
- Docker and Docker Compose (only needed if running the local stack)

Install nipoppy from the repo root — this pulls in all OTel dependencies automatically:

```bash
cd /path/to/nipoppy-otel
pip install -e .
```

---

## Option A — Local Stack

Run everything on your laptop. Good for development and testing.

### 1. Start the stack

```bash
cd server/
docker compose up -d
docker compose ps   # all three containers should show "Up"
```

### 2. Point nipoppy at the local collector

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### 3. Run nipoppy commands

```bash
nipoppy status --dataset /path/to/dataset
nipoppy init   --dataset /path/to/dataset
# etc.
```

### 4. View the dashboard

Open **http://localhost:3000** — credentials `admin / admin`

---

## Option B — Pavot Server (206.12.94.146)

The server is already running the stack. You only need to point your nipoppy at it and open an SSH tunnel to see the dashboard.

### 1. Point nipoppy at the server

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://206.12.94.146:4317
```

### 2. Run nipoppy commands — metrics go directly to the server

```bash
nipoppy status --dataset /path/to/dataset
nipoppy init   --dataset /path/to/dataset
```

### 3. Open SSH tunnel to view Grafana

Grafana (port 3000) is not exposed to the internet. Forward it locally:

```bash
ssh -L 3000:localhost:3000 pavot
```

Then open **http://localhost:3000** — credentials `admin / admin`

You can also forward Prometheus if you want to run PromQL queries directly:

```bash
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 pavot
```

---

## Starting From Scratch

If the dashboard shows stale data or the stack is in a bad state, wipe everything and restart:

### Local

```bash
cd server/
docker compose down -v          # removes containers AND data volumes
docker compose up -d            # fresh start
```

### Server (SSH in first)

```bash
ssh pavot
cd ~/server
docker compose down -v
docker compose up -d
docker compose ps               # confirm all three are Up
```

After a fresh start the dashboard panels will show "No data" until nipoppy commands are run.

---


## Opting Out

```bash
export OTEL_SDK_DISABLED=true
```

nipoppy will run normally with no metrics sent.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Counter stuck at 1 | Check `OTEL_EXPORTER_OTLP_ENDPOINT` has `http://` scheme |
| Grafana unreachable on server | Open SSH tunnel: `ssh -L 3000:localhost:3000 pavot` |
| Collector crash-loop on server | `docker compose down && docker compose up -d` (no `-v`) |
| Want to reset all counts | `docker compose down -v && docker compose up -d` |
