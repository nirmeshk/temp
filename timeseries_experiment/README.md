# Time-Series Storage Experiments (PostgreSQL + Python)

This experiment compares two schemas with the same logical data:
- `naive`: repeated text attributes in every row
- `normalized`: `series_dim` (metadata) + `normalized_readings` (`series_id, metric_name, ts, value`)

Current data shape:
- `4` repeated dimensions: `location`, `region`, `rack`, `team`
- `2` metrics: `temperature_c`, `humidity_pct`
- long `device_id` string to amplify repeated-text storage

## 1) Start PostgreSQL in Docker

```bash
docker run --name ts-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=timeseries_lab \
  -p 5432:5432 \
  -d postgres:16
```

## 2) Install Python dependency

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r experiments/requirements.txt
```

## 3) Run experiment

```bash
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/timeseries_lab'
python experiments/run_experiments.py \
  --series-count 1000 \
  --points-per-series 1440 \
  --step-seconds 10 \
  --json-out experiments/results.json
```

The script prints:
- Storage table (table/index/total size, bytes/row)
- Query performance table (execution time and shared hit blocks)

Implementation split:
- `experiments/sql/setup.sql`: schema and index DDL
- `experiments/run_experiments.py`: data loading and measurements

Series mapping behavior:
- `series_dim` stores a `series_hash` (`sha256` of `device_id|location|region|rack|team`)
- loader looks up by hash, then validates full key columns
- if no exact match is found, it inserts a new series row

## One-command run

Use the wrapper to start/reuse Docker, ensure `.venv`, and run the experiment:

```bash
./experiments/run.sh
```

You can override defaults with env vars:

```bash
SERIES_COUNT=5000 POINTS_PER_SERIES=1440 STEP_SECONDS=10 ./experiments/run.sh
```

## Notes

- `series_count * points_per_series` controls total row volume.
- Increase counts gradually (for example, `1000x1440` then `5000x1440`) to avoid exhausting local resources.
- The script recreates schema `ts_exp` on each run.
