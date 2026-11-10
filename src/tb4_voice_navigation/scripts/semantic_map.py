"""Occupancy-grid geometry and seeded, geodesic segmentation (no ROS dependency)."""
import hashlib
import heapq
import math
from pathlib import Path

import cv2
import numpy as np
import yaml


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


class GridMap:
    def __init__(self, filename):
        self.filename = Path(filename).resolve()
        raw = self.filename.read_bytes()
        data = yaml.safe_load(raw)
        if data.get('mode', 'trinary') != 'trinary':
            raise ValueError('Only trinary maps are supported')
        self.resolution = data['resolution']
        self.origin = data['origin']
        if not finite(self.resolution) or self.resolution <= 0 or len(self.origin) != 3 or not all(map(finite, self.origin)):
            raise ValueError('Invalid map resolution/origin')
        lo, hi = data['free_thresh'], data['occupied_thresh']
        if not finite(lo) or not finite(hi) or not 0 <= lo < hi <= 1:
            raise ValueError('Invalid occupancy thresholds')
        if data.get('negate', 0) not in (0, 1):
            raise ValueError('negate must be 0 or 1')
        self.image_path = self.filename.parent / data['image']
        self.image = cv2.imread(str(self.image_path), cv2.IMREAD_GRAYSCALE)
        if self.image is None:
            raise ValueError(f'Cannot read map image: {self.image_path}')
        self.height, self.width = self.image.shape
        occupancy = self.image.astype(float) / 255.0
        if not data.get('negate', 0):
            occupancy = 1.0 - occupancy
        self.free = occupancy < lo  # unknown is never traversable
        # Padding makes the outside of the image an obstacle, too.
        padded = np.pad(self.free.astype(np.uint8), 1)
        self.clearance = cv2.distanceTransform(padded, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
        # Deduct half a cell diagonal: measure to occupied cell area, not its centre.
        self.clearance = np.maximum(0, self.clearance * self.resolution - self.resolution / math.sqrt(2))
        self.fingerprint = hashlib.sha256(raw + self.image_path.read_bytes()).hexdigest()

    def pixel_to_world(self, u, v):
        x, y = (u + .5) * self.resolution, (self.height - v - .5) * self.resolution
        ox, oy, yaw = self.origin
        c, s = math.cos(yaw), math.sin(yaw)
        return ox + c * x - s * y, oy + s * x + c * y

    def world_to_pixel(self, x, y):
        ox, oy, yaw = self.origin
        c, s = math.cos(yaw), math.sin(yaw)
        dx, dy = x - ox, y - oy
        u = math.floor((c * dx + s * dy) / self.resolution)
        v = self.height - 1 - math.floor((-s * dx + c * dy) / self.resolution)
        if not (0 <= u < self.width and 0 <= v < self.height):
            raise ValueError('Point is outside the map')
        return u, v


def segment(grid, definitions, clearance_m=.4):
    """4-connected multi-source Dijkstra; occupied/unknown pixels stay unlabelled.

    Seeds provide semantics. This is a reproducible functional partition, not
    automatic room recognition. Goal cells share one clearance-eroded component.
    """
    if not finite(clearance_m) or clearance_m <= 0:
        raise ValueError('clearance_m must be positive')
    if not definitions or len(definitions) > 65534:
        raise ValueError('Expected 1..65534 regions')
    labels = np.zeros(grid.free.shape, np.uint16)
    distance = np.full(grid.free.shape, np.inf)
    queue, seeds, ids = [], [], set()
    for index, definition in enumerate(definitions, 1):
        region_id = definition['id']
        if not isinstance(region_id, str) or not region_id or region_id in ids:
            raise ValueError('Region IDs must be unique nonempty strings')
        ids.add(region_id)
        point = definition['seed']
        if len(point) != 2 or not all(map(finite, point)):
            raise ValueError(f'Invalid seed for {region_id}')
        u, v = grid.world_to_pixel(*point)
        if not grid.free[v, u] or distance[v, u] == 0:
            raise ValueError(f'Seed {region_id} must occupy a distinct free cell')
        distance[v, u], labels[v, u] = 0, index
        seeds.append((u, v))
        heapq.heappush(queue, (0, index, v, u))
    while queue:
        cost, index, v, u = heapq.heappop(queue)
        if distance[v, u] != cost or labels[v, u] != index:
            continue
        for dv, du in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nv, nu = v + dv, u + du
            if (0 <= nv < grid.height and 0 <= nu < grid.width and grid.free[nv, nu]
                    and cost + 1 < distance[nv, nu]):
                distance[nv, nu], labels[nv, nu] = cost + 1, index
                heapq.heappush(queue, (cost + 1, index, nv, nu))
    safe = (grid.free & (grid.clearance >= clearance_m)).astype(np.uint8)
    _, components = cv2.connectedComponents(safe, connectivity=4)
    u0, v0 = seeds[0]
    ys, xs = np.nonzero((labels == 1) & safe.astype(bool))
    if not len(xs):
        raise ValueError('First region has no safe goal')
    nearest = np.argmin((xs - u0) ** 2 + (ys - v0) ** 2)
    component = components[ys[nearest], xs[nearest]]
    regions = []
    for index, (definition, (u, v)) in enumerate(zip(definitions, seeds), 1):
        ys, xs = np.nonzero((labels == index) & (components == component))
        if not len(xs):
            raise ValueError(f'Region {definition["id"]} has no safe goal connected to A')
        nearest = np.argmin((xs - u) ** 2 + (ys - v) ** 2)
        gu, gv = int(xs[nearest]), int(ys[nearest])
        x, y = grid.pixel_to_world(gu, gv)
        regions.append(dict(definition, label=index, goal={'x': x, 'y': y, 'yaw': 0.0},
                            goal_pixel=[gu, gv], clearance_m=float(grid.clearance[gv, gu]),
                            area_m2=float(np.count_nonzero(labels == index) * grid.resolution ** 2)))
    return labels, regions


def save_segmentation(grid, definitions, output, clearance_m=.4):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    labels, regions = segment(grid, definitions, clearance_m)
    # Copy original bytes/YAML, making image paths local and metadata relocatable.
    (output / 'map.pgm').write_bytes(grid.image_path.read_bytes())
    metadata = yaml.safe_load(grid.filename.read_text())
    metadata['image'] = 'map.pgm'
    (output / 'map.yaml').write_text(yaml.safe_dump(metadata, sort_keys=False), encoding='utf-8')
    copied = GridMap(output / 'map.yaml')
    data = {'schema_version': 1, 'frame_id': 'map', 'map_yaml': 'map.yaml',
            'map_sha256': copied.fingerprint, 'labels_image': 'labels.png',
            'method': 'seeded_geodesic_voronoi', 'required_clearance_m': clearance_m,
            'unassigned_free_cells': int(np.count_nonzero(grid.free & (labels == 0))),
            'regions': regions}
    (output / 'regions.yaml').write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
    cv2.imwrite(str(output / 'labels.png'), labels)
    overlay = cv2.cvtColor(grid.image, cv2.COLOR_GRAY2BGR)
    palette = [(110, 190, 80), (70, 155, 245), (230, 175, 90), (180, 100, 210)]
    for region in regions:
        mask = labels == region['label']
        color = np.array(palette[(region['label'] - 1) % len(palette)])
        overlay[mask] = (overlay[mask] * .3 + color * .7).astype(np.uint8)
    overlay = cv2.resize(overlay, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    for region in regions:
        u, v = region['goal_pixel']
        center = (u * 2 + 1, v * 2 + 1)
        cv2.circle(overlay, center, 8, (0, 0, 0), 2)
        cv2.putText(overlay, region['id'], (center[0] + 12, center[1] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.imwrite(str(output / 'segmented_map.png'), overlay)
    return data
