#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator

import psycopg


METRICS = (
    ("temperature_c", 20.0, 0.05),
    ("humidity_pct", 45.0, 0.15),
)


@dataclass
class SizeStats:
    name: str
    rows: int
    table_bytes: int
    index_bytes: int
    total_bytes: int

    @property
    def bytes_per_row(self) -> float:
        return self.total_bytes / self.rows if self.rows else 0.0


def human_bytes(num: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{num} B"


def run_sql(cur, sql: str, params=None) -> None:
    cur.execute(sql, params or {})


def setup_schema(cur) -> None:
    sql_path = Path(__file__).parent / "sql" / "setup.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        run_sql(cur, f.read())


def iter_series_keys(series_count: int) -> list[tuple[str, str, str, str, str]]:
    rows = []
    for s in range(1, series_count + 1):
        rows.append(
            (
                f"device-{s:024d}",
                f"location_{s % 50}",
                f"region_{s % 5}",
                f"rack_{s % 100}",
                f"team_{s % 12}",
            )
        )
    return rows


def series_hash(device_id: str, location: str, region: str, rack: str, team: str) -> str:
    series_key = f"{device_id}|{location}|{region}|{rack}|{team}"
    return hashlib.sha256(series_key.encode("utf-8")).hexdigest()


def get_or_create_series_id(
    cur,
    device_id: str,
    location: str,
    region: str,
    rack: str,
    team: str,
) -> int:
    key_hash = series_hash(device_id, location, region, rack, team)
    run_sql(
        cur,
        """
        SELECT series_id, device_id, location, region, rack, team
        FROM ts_exp.series_dim
        WHERE series_hash = %(series_hash)s
        """,
        {"series_hash": key_hash},
    )
    for row in cur.fetchall():
        if row[1:] == (device_id, location, region, rack, team):
            return int(row[0])

    run_sql(
        cur,
        """
        INSERT INTO ts_exp.series_dim (
          series_hash, device_id, location, region, rack, team
        )
        VALUES (
          %(series_hash)s, %(device_id)s, %(location)s, %(region)s, %(rack)s, %(team)s
        )
        RETURNING series_id
        """,
        {
            "series_hash": key_hash,
            "device_id": device_id,
            "location": location,
            "region": region,
            "rack": rack,
            "team": team,
        },
    )
    return int(cur.fetchone()[0])


def iter_naive_rows(
    series_rows: Iterable[tuple[int, str, str, str, str, str]],
    points_per_series: int,
    step_seconds: int,
) -> Iterator[tuple[datetime, str, str, str, str, str, str, float]]:
    start_ts = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    step = timedelta(seconds=step_seconds)
    for series_id, device_id, location, region, rack, team in series_rows:
        ts = start_ts
        series_offset = (series_id % 10) * 0.1
        for _ in range(points_per_series):
            epoch_mod = int(ts.timestamp()) % 300
            for metric_name, base_value, jitter_scale in METRICS:
                value = base_value + series_offset + (epoch_mod * jitter_scale / 100.0)
                yield (ts, device_id, location, region, rack, team, metric_name, value)
            ts += step


def iter_normalized_rows(
    series_rows: Iterable[tuple[int, str, str, str, str, str]],
    points_per_series: int,
    step_seconds: int,
) -> Iterator[tuple[int, str, datetime, float]]:
    start_ts = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    step = timedelta(seconds=step_seconds)
    for series_id, _, _, _, _, _ in series_rows:
        ts = start_ts
        series_offset = (series_id % 10) * 0.1
        for _ in range(points_per_series):
            epoch_mod = int(ts.timestamp()) % 300
            for metric_name, base_value, jitter_scale in METRICS:
                value = base_value + series_offset + (epoch_mod * jitter_scale / 100.0)
                yield (series_id, metric_name, ts, value)
            ts += step


def iter_normalized_rows_hc(
    series_rows: Iterable[tuple[int, str, str, str, str, str]],
    points_per_series: int,
    step_seconds: int,
) -> Iterator[tuple[int, datetime, str, float, str]]:
    start_ts = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
    step = timedelta(seconds=step_seconds)
    import uuid
    for series_id, _, _, _, _, _ in series_rows:
        ts = start_ts
        series_offset = (series_id % 10) * 0.1
        for _ in range(points_per_series):
            epoch_mod = int(ts.timestamp()) % 300
            for metric_name, base_value, jitter_scale in METRICS:
                value = base_value + series_offset + (epoch_mod * jitter_scale / 100.0)
                yield (series_id, ts, metric_name, value, str(uuid.uuid4()))
            ts += step


def load_data(cur, series_count: int, points_per_series: int, step_seconds: int) -> None:
    series_rows: list[tuple[int, str, str, str, str, str]] = []
    for device_id, location, region, rack, team in iter_series_keys(series_count):
        sid = get_or_create_series_id(cur, device_id, location, region, rack, team)
        series_rows.append((sid, device_id, location, region, rack, team))

    with cur.copy(
        "COPY ts_exp.naive_readings (ts, device_id, location, region, rack, team, metric_name, value) FROM STDIN"
    ) as copy:
        for row in iter_naive_rows(series_rows, points_per_series, step_seconds):
            copy.write_row(row)

    with cur.copy(
        "COPY ts_exp.normalized_readings (series_id, metric_name, ts, value) FROM STDIN"
    ) as copy:
        for row in iter_normalized_rows(series_rows, points_per_series, step_seconds):
            copy.write_row(row)

    with cur.copy(
        "COPY ts_exp.normalized_readings_hc (series_id, ts, metric_name, value, request_id) FROM STDIN"
    ) as copy:
        for row in iter_normalized_rows_hc(series_rows, points_per_series, step_seconds):
            copy.write_row(row)

    run_sql(cur, "ANALYZE ts_exp.naive_readings;")
    run_sql(cur, "ANALYZE ts_exp.series_dim;")
    run_sql(cur, "ANALYZE ts_exp.normalized_readings;")
    run_sql(cur, "ANALYZE ts_exp.normalized_readings_hc;")


def get_size_stats(cur, relname: str) -> SizeStats:
    run_sql(
        cur,
        """
        SELECT
          c.reltuples::bigint AS rows_estimate,
          pg_relation_size(%(rel)s::regclass) AS table_bytes,
          pg_indexes_size(%(rel)s::regclass) AS index_bytes,
          pg_total_relation_size(%(rel)s::regclass) AS total_bytes
        FROM pg_class c
        WHERE c.oid = %(rel)s::regclass;
        """,
        {"rel": relname},
    )
    row = cur.fetchone()
    return SizeStats(
        name=relname,
        rows=int(row[0]),
        table_bytes=int(row[1]),
        index_bytes=int(row[2]),
        total_bytes=int(row[3]),
    )


def explain_ms_and_buffers(cur, sql: str, params=None) -> tuple[float, int]:
    run_sql(cur, f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", params or {})
    explain = cur.fetchone()[0]
    plan = explain[0]
    exec_ms = float(plan["Execution Time"])
    shared_hits = int(plan["Plan"].get("Shared Hit Blocks", 0))
    return exec_ms, shared_hits


def print_size_report(naive: SizeStats, normalized: SizeStats) -> None:
    print("\nStorage summary")
    print(
        "| schema | rows | table size | index size | total size | bytes/row |\n"
        "|---|---:|---:|---:|---:|---:|"
    )
    for stats in (naive, normalized):
        label = "naive" if "naive" in stats.name else "normalized"
        print(
            f"| {label} | {stats.rows:,} | {human_bytes(stats.table_bytes)} "
            f"| {human_bytes(stats.index_bytes)} | {human_bytes(stats.total_bytes)} "
            f"| {stats.bytes_per_row:.2f} |"
        )


def combine_size_stats(name: str, base_rows: int, stats: list[SizeStats]) -> SizeStats:
    return SizeStats(
        name=name,
        rows=base_rows,
        table_bytes=sum(s.table_bytes for s in stats),
        index_bytes=sum(s.index_bytes for s in stats),
        total_bytes=sum(s.total_bytes for s in stats),
    )


def print_query_report(cur, start_ts: datetime, end_ts: datetime) -> None:
    device = "device-" + "42".zfill(24)
    metric = "temperature_c"
    print("\nQuery performance (single run, warm cache)")
    print("| query | schema | execution ms | shared hit blocks |")
    print("|---|---|---:|---:|")

    q1_naive = """
      SELECT ts, value
      FROM ts_exp.naive_readings
      WHERE device_id = %(device)s
        AND metric_name = %(metric)s
        AND ts BETWEEN %(start_ts)s AND %(end_ts)s
      ORDER BY ts
    """
    ms, hits = explain_ms_and_buffers(
        cur,
        q1_naive,
        {"device": device, "metric": metric, "start_ts": start_ts, "end_ts": end_ts},
    )
    print(f"| range read | naive | {ms:.2f} | {hits} |")

    q1_norm = """
      SELECT r.ts, r.value
      FROM ts_exp.normalized_readings r
      JOIN ts_exp.series_dim d ON d.series_id = r.series_id
      WHERE d.device_id = %(device)s
        AND r.metric_name = %(metric)s
        AND r.ts BETWEEN %(start_ts)s AND %(end_ts)s
      ORDER BY r.ts
    """
    ms, hits = explain_ms_and_buffers(
        cur,
        q1_norm,
        {"device": device, "metric": metric, "start_ts": start_ts, "end_ts": end_ts},
    )
    print(f"| range read | normalized | {ms:.2f} | {hits} |")

    q2_naive = """
      SELECT date_trunc('hour', ts) AS bucket, avg(value)
      FROM ts_exp.naive_readings
      WHERE metric_name = %(metric)s
        AND ts BETWEEN %(start_ts)s AND %(end_ts)s
      GROUP BY bucket
      ORDER BY bucket
    """
    ms, hits = explain_ms_and_buffers(
        cur, q2_naive, {"metric": metric, "start_ts": start_ts, "end_ts": end_ts}
    )
    print(f"| hourly avg | naive | {ms:.2f} | {hits} |")

    q2_norm = """
      SELECT date_trunc('hour', r.ts) AS bucket, avg(r.value)
      FROM ts_exp.normalized_readings r
      WHERE r.metric_name = %(metric)s
        AND r.ts BETWEEN %(start_ts)s AND %(end_ts)s
      GROUP BY bucket
      ORDER BY bucket
    """
    ms, hits = explain_ms_and_buffers(
        cur, q2_norm, {"metric": metric, "start_ts": start_ts, "end_ts": end_ts}
    )
    print(f"| hourly avg | normalized | {ms:.2f} | {hits} |")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Postgres time-series storage experiments.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--series-count", type=int, default=1000)
    parser.add_argument("--points-per-series", type=int, default=1440)
    parser.add_argument("--step-seconds", type=int, default=10)
    parser.add_argument("--skip-load", action="store_true")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL is required (or pass --database-url).")

    window_end = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)
    window_start = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)

    with psycopg.connect(args.database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            setup_schema(cur)
            if not args.skip_load:
                load_data(cur, args.series_count, args.points_per_series, args.step_seconds)

            naive = get_size_stats(cur, "ts_exp.naive_readings")
            normalized_readings = get_size_stats(cur, "ts_exp.normalized_readings")
            normalized_meta = get_size_stats(cur, "ts_exp.series_dim")
            normalized = combine_size_stats(
                name="ts_exp.normalized_total",
                base_rows=normalized_readings.rows,
                stats=[normalized_readings, normalized_meta],
            )
            print_size_report(naive, normalized)
            print_query_report(cur, window_start, window_end)

            if args.json_out:
                payload = {
                    "generated_at": datetime.now(tz=timezone.utc).isoformat(),
                    "config": {
                        "series_count": args.series_count,
                        "points_per_series": args.points_per_series,
                        "step_seconds": args.step_seconds,
                    },
                    "storage": {
                        "naive": naive.__dict__ | {"bytes_per_row": naive.bytes_per_row},
                        "normalized": normalized.__dict__ | {"bytes_per_row": normalized.bytes_per_row},
                        "normalized_breakdown": {
                            "readings": normalized_readings.__dict__
                            | {"bytes_per_row": normalized_readings.bytes_per_row},
                            "series_metadata": normalized_meta.__dict__
                            | {"bytes_per_row": normalized_meta.bytes_per_row},
                        },
                    },
                }
                with open(args.json_out, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                print(f"\nWrote JSON summary to {args.json_out}")


if __name__ == "__main__":
    main()
