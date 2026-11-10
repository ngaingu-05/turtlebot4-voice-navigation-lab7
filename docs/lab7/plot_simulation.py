"""Plot measured Gazebo positions from the text-command Nav2 check."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1] / 'src/tb4_voice_navigation'
sys.path.insert(0, str(PACKAGE / 'scripts'))
from semantic_map import GridMap
from voice_core import RegionCatalog

grid = GridMap(PACKAGE / 'maps/map.yaml')
data = json.loads((HERE / 'simulation.json').read_text())
catalog = RegionCatalog.load(PACKAGE / 'maps/regions.yaml')
fig, ax = plt.subplots(figsize=(9, 7))
ox, oy, yaw = grid.origin
if yaw != 0:
    raise ValueError('This plotting helper expects the shipped zero-yaw Depot map')
ax.imshow(grid.image, cmap='gray', vmin=0, vmax=255,
          extent=[ox, ox + grid.width * grid.resolution, oy, oy + grid.height * grid.resolution])
ax.plot([p['x'] for p in data['poses']], [p['y'] for p in data['poses']],
        color='#007e87', linewidth=2, label='Measured Gazebo trajectory')
first = data['poses'][0]
ax.scatter([first['x']], [first['y']], marker='s', color='#19384b', zorder=4, label='Start after undock')
for rid, region in catalog.regions.items():
    goal = region['goal']
    ax.scatter([goal['x']], [goal['y']], marker='x', s=90, linewidths=2.5, color='#db6a18', zorder=5)
    ax.annotate(rid, (goal['x'], goal['y']), xytext=(9, 9), textcoords='offset points', fontsize=13, weight='bold')
ax.set(xlim=(-3.6, 3.8), ylim=(-4.1, 4.1), xlabel='map x (m)', ylabel='map y (m)',
       title='Nav2 in Gazebo: A, A → B, C\nInput: ROS text commands; no microphone in this check')
ax.set_aspect('equal')
ax.grid(alpha=.2)
ax.legend(loc='upper left')
fig.tight_layout()
fig.savefig(HERE / 'trajectory.png', dpi=160)
print(HERE / 'trajectory.png')
