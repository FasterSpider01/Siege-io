
import os
import json
import time
import random
import math
from http.server import SimpleHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')

players = {}
bullets = []
orbs = []
structures = []
MAP_WIDTH = 2500
MAP_HEIGHT = 2500

types = ['xp', 'xp', 'xp', 'health', 'speed', 'damage']
for i in range(60):
    orbs.append({
        'id': f"orb_{i}",
        'x': random.randint(100, MAP_WIDTH - 100),
        'y': random.randint(100, MAP_HEIGHT - 100),
        'type': random.choice(types)
    })

def update_game_physics():
    now = time.time()
    
    for s in structures[:]:
        if s['hp'] <= 0 or now > s['expire']:
            structures.remove(s)

    for b in bullets[:]:
        b['x'] += b['vx']
        b['y'] += b['vy']
        b['life'] -= 1
        
        hit_struct = False
        for s in structures[:]:
            if math.hypot(b['x'] - s['x'], b['y'] - s['y']) < s['radius']:
                s['hp'] -= b['damage']
                if b in bullets:
                    bullets.remove(b)
                hit_struct = True
                break
        if hit_struct:
            continue

        for pid, p in list(players.items()):
            if p['hp'] <= 0 or pid == b['owner'] or p.get('shield', False):
                continue
            if math.hypot(b['x'] - p['x'], b['y'] - p['y']) < 28:
                p['hp'] -= b['damage']
                if b in bullets:
                    bullets.remove(b)
                if p['hp'] <= 0:
                    p['hp'] = 0
                    killer = players.get(b['owner'])
                    if killer:
                        killer['score'] += 300
                        killer['xp'] += 150
                        next_xp = killer['level'] * 200
                        if killer['xp'] >= next_xp and killer['level'] < 20:
                            killer['level'] += 1
                            killer['maxHp'] += 15
                            killer['hp'] = killer['maxHp']
                break
                
        if b['life'] <= 0 and b in bullets:
            bullets.remove(b)

    for o in orbs[:]:
        for pid, p in list(players.items()):
            if p['hp'] <= 0:
                continue
            if math.hypot(o['x'] - p['x'], o['y'] - p['y']) < 30:
                if o['type'] == 'xp':
                    p['xp'] += 45
                    p['score'] += 45
                    next_xp = p['level'] * 200
                    if p['xp'] >= next_xp and p['level'] < 20:
                        p['level'] += 1
                        p['maxHp'] += 15
                        p['hp'] = p['maxHp']
                elif o['type'] == 'health':
                    p['hp'] = min(p['maxHp'], p['hp'] + 40)
                elif o['type'] == 'speed':
                    p['speed'] = min(9.0, p['speed'] + 0.4)
                elif o['type'] == 'damage':
                    p['damageBoost'] = 2.0
                
                orbs.remove(o)
                orbs.append({
                    'id': f"orb_{now}_{random.randint(10,99)}",
                    'x': random.randint(100, MAP_WIDTH - 100),
                    'y': random.randint(100, MAP_HEIGHT - 100),
                    'type': random.choice(types)
                })
                break

class SiegeGameHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
        data = json.loads(body) if body else {}

        update_game_physics()
        now = time.time()
        response = {}

        if self.path == '/api/join':
            pid = f"p_{int(now * 1000)}_{random.randint(100, 999)}"
            base_hp = 120
            
            players[pid] = {
                'id': pid,
                'name': data.get('name', 'Hero')[:12],
                'x': random.randint(300, MAP_WIDTH - 300),
                'y': random.randint(300, MAP_HEIGHT - 300),
                'angle': 0,
                'hp': base_hp,
                'maxHp': base_hp,
                'level': 1,
                'xp': 0,
                'score': 0,
                'speed': 5.5,
                'shield': True,
                'shieldEnd': now + 3.0,
                'damageBoost': 1.0,
                'lastActive': now,
                'lastBuild': 0
            }
            response = {
                'id': pid, 
                'mapWidth': MAP_WIDTH, 
                'mapHeight': MAP_HEIGHT,
                'players': players,
                'orbs': orbs,
                'structures': structures
            }

        elif self.path == '/api/update':
            pid = data.get('id')
            p = players.get(pid)
            if p:
                p['lastActive'] = now
                if p['hp'] > 0:
                    p['x'] = max(30, min(MAP_WIDTH - 30, data.get('x', p['x'])))
                    p['y'] = max(30, min(MAP_HEIGHT - 30, data.get('y', p['y'])))
                    p['angle'] = data.get('angle', p['angle'])
                    
                    if p['shield'] and now > p['shieldEnd']:
                        p['shield'] = False

                    if data.get('shoot'):
                        angle = data['shootAngle']
                        bullets.append({
                            'id': f"b_{pid}_{now}",
                            'owner': pid,
                            'x': p['x'] + math.cos(angle) * 25,
                            'y': p['y'] + math.sin(angle) * 25,
                            'vx': math.cos(angle) * 16,
                            'vy': math.sin(angle) * 16,
                            'damage': 20 * p['damageBoost'],
                            'life': 45
                        })

                    if data.get('buildItem'):
                        if now - p.get('lastBuild', 0) > 1.5:
                            p['lastBuild'] = now
                            b_type = data.get('buildType', 'Wood Wall')
                            hp_map = {
                                'Wood Wall': 150, 'Stone Wall': 300, 'Iron Wall': 500,
                                'Spike Trap': 100, 'Gate': 200, 'Healing Totem': 120,
                                'Speed Pad': 100, 'Mini Turret': 250, 'Shield Gen': 300,
                                'Mine': 80, 'Radar Tower': 200, 'Barbed Wire': 150,
                                'Bounce Pad': 100, 'Ammo Station': 200, 'Flame Trap': 150,
                                'Ice Trap': 150, 'Teleporter': 250, 'Mortar': 300,
                                'Tesla Coil': 280, 'Vault': 600
                            }
                            max_h = hp_map.get(b_type, 200)
                            structures.append({
                                'id': f"s_{pid}_{now}",
                                'owner': pid,
                                'type': b_type,
                                'x': p['x'],
                                'y': p['y'],
                                'hp': max_h,
                                'maxHp': max_h,
                                'radius': 40,
                                'expire': now + 45.0
                            })
                else:
                    if pid in players:
                        del players[pid]

            for key, player in list(players.items()):
                if now - player.get('lastActive', 0) > 5.0 or player.get('hp', 0) <= 0:
                    if key in players:
                        del players[key]

            response = {
                'players': players,
                'bullets': bullets,
                'orbs': orbs,
                'structures': structures
            }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

if __name__ == "__main__":
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer((host, port), SiegeGameHandler)
    print(f"Starting server on http://{host}:{port}")
    server.serve_forever()
