import pandas as pd
import numpy as np
import os
import uuid
import pyarrow.parquet as pq

def get_file_size_mb(file_path):
    return os.path.getsize(file_path) / (1024 * 1024)

num_series = 1000
points_per_series = 1440
total_rows = num_series * points_per_series

print(f"Generating {total_rows:,} rows of realistic data...")

# Correct way to handle unique timestamps per series
start_time = np.datetime64("2026-02-11T10:00:00")
time_steps = np.arange(points_per_series) * np.timedelta64(10, 's')
series_offsets = np.arange(num_series) * np.timedelta64(1, 'ns')

all_ts = []
for offset in series_offsets:
    # Each series gets the same time steps but offset by 1ns to ensure global uniqueness
    all_ts.append(start_time + time_steps + offset)

all_ts = np.concatenate(all_ts)

# Values: Add random noise to ensure every value is unique
values = 20.0 + np.random.normal(0, 0.5, total_rows)

# Dimensions: Stable identifiers (1000 unique device_ids)
device_ids = np.repeat([f"device-{i:04d}" for i in range(num_series)], points_per_series)
locations = np.repeat([f"loc-{i%50}" for i in range(num_series)], points_per_series)

df = pd.DataFrame({
    'ts': all_ts,
    'device_id': device_ids,
    'location': locations,
    'value': values
})

# Add High Cardinality Column
df['request_id'] = [str(uuid.uuid4()) for _ in range(total_rows)]

parquet_file = "readings_refined.parquet"
df.to_parquet(parquet_file, compression='snappy', index=False)
print(f"Saved refined Parquet: {parquet_file} ({get_file_size_mb(parquet_file):.2f} MB)")

parquet_obj = pq.ParquetFile(parquet_file)
rg = parquet_obj.metadata.row_group(0)

print("\nColumn Encoding Breakdown:")
print("{:<15} | {:<12} | {}".format('Column', 'Compression', 'Encodings'))
print("-" * 65)
for i in range(rg.num_columns):
    col = rg.column(i)
    encs = [str(e) for e in col.encodings]
    print("{:<15} | {:<12} | {}".format(col.path_in_schema, col.compression, ', '.join(encs)))
