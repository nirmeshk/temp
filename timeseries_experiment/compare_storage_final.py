import psycopg
import pandas as pd
import os
import pyarrow.parquet as pq

def get_file_size_mb(file_path):
    return os.path.getsize(file_path) / (1024 * 1024)

conn_info = 'dbname=postgres user=postgres host=localhost password=postgres'

with psycopg.connect(conn_info) as conn:
    # 1. Baseline Comparison (Normalized vs Parquet)
    print("Exporting Baseline (Normalized) to Parquet...")
    df_base = pd.read_sql_query("SELECT series_id, ts, metric_name, value FROM ts_exp.normalized_readings", conn)
    df_base.to_parquet("normalized_base.parquet", compression='snappy', index=False)
    
    # 2. High Cardinality Comparison (Normalized HC vs Parquet)
    print("Exporting High Cardinality to Parquet...")
    df_hc = pd.read_sql_query("SELECT series_id, ts, metric_name, value, request_id FROM ts_exp.normalized_readings_hc", conn)
    df_hc.to_parquet("normalized_hc.parquet", compression='snappy', index=False)

    # Get Postgres sizes from the DB
    def get_pg_size(cur, table):
        cur.execute(f"SELECT pg_total_relation_size('{table}')")
        return cur.fetchone()[0] / (1024 * 1024)

    with conn.cursor() as cur:
        pg_norm_size = get_pg_size(cur, 'ts_exp.normalized_readings')
        pg_hc_size = get_pg_size(cur, 'ts_exp.normalized_readings_hc')
        pg_meta_size = get_pg_size(cur, 'ts_exp.series_dim')

print("\n" + "="*60)
print("FINAL STORAGE SHOWDOWN: POSTGRES NORMALIZED VS PARQUET")
print("="*60)
print(f"{'Scenario':<25} | {'Postgres Total':<15} | {'Parquet Size':<15}")
print("-" * 60)
# Baseline: Postgres Normalized Total (Table + Meta) vs Parquet
print(f"{'Baseline (Repetitive)':<25} | {pg_norm_size + pg_meta_size:<15.2f} MB | {get_file_size_mb('normalized_base.parquet'):<15.2f} MB")
# High Cardinality: Postgres HC Total (Table + Meta) vs Parquet
print(f"{'High Card (with UUID)':<25} | {pg_hc_size + pg_meta_size:<15.2f} MB | {get_file_size_mb('normalized_hc.parquet'):<15.2f} MB")
print("="*60)
