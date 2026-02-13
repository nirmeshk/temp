import matplotlib.pyplot as plt

# Data for Thermostat A (Living Room)
times_a = ["10:00:00", "10:00:10", "10:00:20", "10:00:30"]
values_a = [21.1, 21.1, 21.2, 21.1]

# Data for Thermostat B (Bedroom)
times_b = ["10:00:00", "10:00:10", "10:00:20", "10:00:30"]
values_b = [20.5, 20.6, 20.6, 20.7]

plt.figure(figsize=(10, 5))

# Plot with non-redundant labels
plt.plot(times_a, values_a, marker='o', linestyle='-', label='device=thermostat, location=living_room', color='#1f77b4', linewidth=2)
plt.plot(times_b, values_b, marker='s', linestyle='--', label='device=thermostat, location=bedroom', color='#ff7f0e', linewidth=2)

# Styling with updated title
plt.title('Example: Multiple Series in a Time-Series Database', fontsize=14, pad=15)
plt.xlabel('Timestamp', fontsize=12)
plt.ylabel('Temperature (°C)', fontsize=12)
plt.ylim(20.0, 21.5)
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend(frameon=True, loc='upper left', fontsize=10)

plt.tight_layout()
plt.savefig('timeseries_visualization.png', dpi=300)
print("Updated chart with new title saved as timeseries_visualization.png")
