import math
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest
import yaml

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
from semantic_map import GridMap, save_segmentation, segment
from voice_core import CommandError, RegionCatalog


@pytest.fixture
def catalog():
    return RegionCatalog.load(PACKAGE / 'maps/regions.yaml')


@pytest.mark.parametrize('text,expected', [
    ('Đi đến khu vực A.', ['A']),
    ('Di chuyển từ khu vực A đến khu vực B.', ['A', 'B']),
    ('Đi đến phòng thí nghiệm.', ['B']),
    ('Đi từ phòng A qua hành lang C rồi đến phòng B', ['A', 'C', 'B']),
    ('DI CHUYEN TU A TOI B', ['A', 'B']),
    ('đi tới HÀNH LANG', ['C']),
    ('Đi đến khu vực bê', ['B']),
    ('Đi đến vùng A', ['A']),
    ('Đi đến vùng B', ['B']),
    ('Đi đến vùng C', ['C']),
    ('Đi từ vùng A qua vùng C rồi đến vùng B', ['A', 'C', 'B']),
    ('Đi đến vùng bê', ['B']),
    ('Đi đến vùng xê', ['C']),
    ('Dừng lại!', None),
    ('Hủy lệnh.', None),
])
def test_commands(catalog, text, expected):
    assert catalog.parse(text) == expected


@pytest.mark.parametrize('text', [
    'Đi đến khu vực D', 'Đi đến vùng Z', 'Di chuyển từ A đến phòng không có',
    'Đi từ A qua khu Z rồi đến B', 'Đi đến khu vực AA',
    'Không đi đến A', 'Đừng đi đến A', 'Đi đến A hoặc B',
    'Hôm nay phòng A mở cửa', 'A', '', 'Đi đến', 'Đi từ A',
    'Đi đến A rồi', 'Đi đến phòng thí nghiệm phía sau',
])
def test_invalid_commands_are_atomic(catalog, text):
    with pytest.raises(CommandError):
        catalog.parse(text)


def make_map(tmp_path, image=None, **overrides):
    if image is None:
        image = np.full((50, 60), 254, np.uint8)
        image[0, :] = image[-1, :] = image[:, 0] = image[:, -1] = 0
    cv2.imwrite(str(tmp_path / 'input.pgm'), image)
    metadata = dict(image='input.pgm', mode='trinary', resolution=.1,
                    origin=[-2., -3., 0.], negate=0, occupied_thresh=.65, free_thresh=.196)
    metadata.update(overrides)
    path = tmp_path / 'input.yaml'
    path.write_text(yaml.safe_dump(metadata))
    return GridMap(path)


@pytest.mark.parametrize('yaw', [0., math.pi / 2, -.7])
def test_pixel_world_roundtrip_and_bounds(tmp_path, yaw):
    grid = make_map(tmp_path, origin=[-2., -3., yaw])
    for u, v in [(0, 0), (59, 49), (30, 20)]:
        assert grid.world_to_pixel(*grid.pixel_to_world(u, v)) == (u, v)
    with pytest.raises(ValueError):
        grid.world_to_pixel(100, 100)


def test_unknown_negate_and_edge_clearance(tmp_path):
    image = np.array([[254, 205, 0], [254, 254, 254]], dtype=np.uint8)
    grid = make_map(tmp_path, image)
    assert grid.free[0].tolist() == [True, False, False]
    assert grid.clearance[0, 0] < .1
    negated = make_map(tmp_path, 255 - image, negate=1)
    np.testing.assert_array_equal(grid.free, negated.free)


def test_segmentation_does_not_cross_walls_and_goals_have_clearance(tmp_path):
    grid = make_map(tmp_path)
    grid.free[5:45, 30] = False
    definitions = [dict(id=rid, name=rid, seed=list(grid.pixel_to_world(u, v)))
                   for rid, u, v in [('A', 10, 10), ('B', 45, 10), ('C', 10, 35)]]
    labels, regions = segment(grid, definitions, clearance_m=.3)
    assert set(np.unique(labels)) == {0, 1, 2, 3}
    assert np.all(labels[~grid.free] == 0)
    for region in regions:
        u, v = region['goal_pixel']
        assert labels[v, u] == region['label']
        assert grid.clearance[v, u] >= .3
    repeated, _ = segment(grid, definitions, clearance_m=.3)
    np.testing.assert_array_equal(labels, repeated)


def test_disconnected_regions_rejected(tmp_path):
    image = np.full((50, 60), 254, np.uint8)
    image[:, 30] = 0
    grid = make_map(tmp_path, image)
    definitions = [dict(id=rid, name=rid, seed=list(grid.pixel_to_world(u, 20)))
                   for rid, u in [('A', 10), ('B', 45)]]
    with pytest.raises(ValueError, match='connected'):
        segment(grid, definitions, .3)


def test_saved_map_is_portable_and_detects_changes(tmp_path):
    grid = make_map(tmp_path)
    definitions = [dict(id='A', name='Phòng A', seed=list(grid.pixel_to_world(20, 20)))]
    out = tmp_path / 'out'
    save_segmentation(grid, definitions, out, .3)
    assert RegionCatalog.load(out / 'regions.yaml').parse('Đi đến phòng A') == ['A']
    metadata = yaml.safe_load((out / 'map.yaml').read_text())
    metadata['origin'][0] += .1
    (out / 'map.yaml').write_text(yaml.safe_dump(metadata))
    with pytest.raises(ValueError, match='Map changed'):
        RegionCatalog.load(out / 'regions.yaml')


def test_ambiguous_alias_and_invalid_goal_rejected():
    regions = [dict(id='A', name='Phòng', goal=dict(x=0., y=0., yaw=0.)),
               dict(id='B', name='Phòng', goal=dict(x=1., y=0., yaw=0.))]
    with pytest.raises(ValueError, match='ambiguous'):
        RegionCatalog(dict(frame_id='map', regions=regions))
    regions[0]['goal']['x'] = float('nan')
    with pytest.raises(ValueError, match='Invalid goal'):
        RegionCatalog(dict(frame_id='map', regions=regions[:1]))


def test_shipped_goals_are_in_same_safe_component(catalog):
    grid = GridMap(PACKAGE / 'maps/map.yaml')
    safe = (grid.free & (grid.clearance >= catalog.data['required_clearance_m'])).astype(np.uint8)
    _, components = cv2.connectedComponents(safe, connectivity=4)
    found = set()
    for region in catalog.regions.values():
        u, v = grid.world_to_pixel(region['goal']['x'], region['goal']['y'])
        assert components[v, u] > 0
        found.add(int(components[v, u]))
    assert len(found) == 1
