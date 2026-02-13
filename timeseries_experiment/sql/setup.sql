DROP SCHEMA IF EXISTS ts_exp CASCADE;
CREATE SCHEMA ts_exp;

CREATE TABLE ts_exp.naive_readings (
  ts timestamptz NOT NULL,
  device_id text NOT NULL,
  location text NOT NULL,
  region text NOT NULL,
  rack text NOT NULL,
  team text NOT NULL,
  metric_name text NOT NULL,
  value double precision NOT NULL
);

CREATE INDEX idx_naive_ts ON ts_exp.naive_readings (ts);
CREATE INDEX idx_naive_device_metric_ts
  ON ts_exp.naive_readings (device_id, metric_name, ts);

CREATE TABLE ts_exp.series_dim (
  series_id bigserial PRIMARY KEY,
  series_hash text NOT NULL,
  device_id text NOT NULL,
  location text NOT NULL,
  region text NOT NULL,
  rack text NOT NULL,
  team text NOT NULL
);

CREATE INDEX idx_series_dim_hash ON ts_exp.series_dim (series_hash);
CREATE INDEX idx_series_dim_device ON ts_exp.series_dim (device_id);

CREATE TABLE ts_exp.normalized_readings (
  series_id integer NOT NULL REFERENCES ts_exp.series_dim(series_id),
  metric_name text NOT NULL,
  ts timestamptz NOT NULL,
  value double precision NOT NULL
);

CREATE INDEX idx_norm_series_metric_ts
  ON ts_exp.normalized_readings (series_id, metric_name, ts);
CREATE INDEX idx_norm_ts ON ts_exp.normalized_readings (ts);

-- New table for High Cardinality comparison
CREATE TABLE ts_exp.normalized_readings_hc (
  series_id integer NOT NULL REFERENCES ts_exp.series_dim(series_id),
  ts timestamptz NOT NULL,
  metric_name text NOT NULL,
  value double precision NOT NULL,
  request_id text NOT NULL
);

CREATE INDEX idx_hc_series_ts ON ts_exp.normalized_readings_hc (series_id, ts);
