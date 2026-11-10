"""Strict Vietnamese command grammar; atomic validation before any Nav2 action."""
import re
import unicodedata
from pathlib import Path

import cv2
import yaml

from semantic_map import GridMap, finite


def normalize(text):
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd').replace('Đ', 'd'))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9\s]', ' ', text).split())


class CommandError(ValueError):
    pass


class RegionCatalog:
    def __init__(self, data):
        if data.get('frame_id') != 'map' or not data.get('regions'):
            raise ValueError('Expected nonempty semantic regions in map frame')
        self.data, self.regions, self.aliases = data, {}, {}
        for region in data['regions']:
            rid = region['id']
            if not isinstance(rid, str) or not rid or rid in self.regions:
                raise ValueError('Region IDs must be unique strings')
            goal = region['goal']
            if any(not finite(goal.get(k)) for k in ('x', 'y', 'yaw')):
                raise ValueError(f'Invalid goal for {rid}')
            self.regions[rid] = region
            for alias in [rid, region['name'], *region.get('aliases', [])]:
                key = normalize(alias)
                if not key or (key in self.aliases and self.aliases[key] != rid):
                    raise ValueError(f'Empty or ambiguous region alias: {alias}')
                self.aliases[key] = rid

    @classmethod
    def load(cls, filename):
        path = Path(filename).resolve()
        data = yaml.safe_load(path.read_text(encoding='utf-8'))
        catalog = cls(data)
        grid = GridMap(path.parent / data['map_yaml'])
        if grid.fingerprint != data['map_sha256']:
            raise ValueError('Map changed: regenerate segmentation')
        labels = cv2.imread(str(path.parent / data['labels_image']), cv2.IMREAD_UNCHANGED)
        if labels is None or labels.shape != grid.free.shape:
            raise ValueError('Missing/invalid region label image')
        required = data['required_clearance_m']
        if not finite(required) or required <= 0:
            raise ValueError('Invalid clearance requirement')
        for region in catalog.regions.values():
            u, v = grid.world_to_pixel(region['goal']['x'], region['goal']['y'])
            if labels[v, u] != region['label'] or not grid.free[v, u] or grid.clearance[v, u] < required:
                raise ValueError(f'Unsafe or incorrectly labelled goal: {region["id"]}')
        return catalog

    def resolve(self, phrase):
        phrase = normalize(phrase)
        if phrase not in self.aliases:
            raise CommandError(f'Khu vực không tồn tại: {phrase or "(trống)"}')
        return self.aliases[phrase]

    def parse(self, text):
        text = normalize(text)
        if text in ('dung', 'dung lai', 'huy', 'huy lenh', 'dung robot'):
            return None
        if re.search(r'\b(khong|dung di|chua|neu|hay la|hoac)\b', text):
            raise CommandError('Lệnh phủ định hoặc mơ hồ; hãy nói rõ một tuyến đường')
        # Require an explicit movement verb. Merely mentioning a room never moves.
        match = re.fullmatch(r'(?:di chuyen|di)(?:\s+)(.+)', text)
        if not match:
            raise CommandError('Dùng: Đi đến <vùng>, hoặc Di chuyển từ <vùng> đến <vùng>')
        body = match[1]
        if body.startswith('tu '):
            body = body[3:]
            if not re.search(r'\s+(?:den|toi)\s+', body):
                raise CommandError('Lệnh từ một vùng cần có đích đến')
        elif body.startswith('den '):
            body = body[4:]
        elif body.startswith('toi '):
            body = body[4:]
        else:
            raise CommandError('Thiếu từ đến hoặc từ')
        parts = re.split(r'\s+(?:roi den|roi toi|roi|qua|den|toi)\s+', body)
        if len(parts) > 8:
            raise CommandError('Tối đa 8 điểm trong một lệnh')
        # Resolve every part before returning; unknown intermediate stops whole route.
        return [self.resolve(part) for part in parts]
