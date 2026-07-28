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
MAP_WIDTH = 2500
MAP_HEIGHT = 2500

types = ['xp', 'xp', 'xp', 'health', 'speed', 'damage']
for i in range(50):
    orbs.append({
        'id': f"orb_{i}",
        'x': random.randint(100, MAP_WIDTH - 100),
        'y': random.randint(100, MAP_HEIGHT - 100),
        'type': random.choice(types)
    })

def update_game_physics():
    now = time.time()
    
    # Update Bullets
    for b in bullets[:]:
        b['x'] += b['vx']
        b['y'] += b['vy']
        b['life'] -= 1
        
        for pid, p in list(players.items()):
            if p['hp'] <= 0 or pid == b['owner'] or p.get('shield', False):
                continue
            if math.hypot(b['x'] - p['x'], b['y'] - p['y']) < 28:
                p['hp'] -= b['damage']
                if b in bullets:
                    bullets.remove(b)
                if p['hp'] <= 0:
                    killer = players.get(b['owner'])
                    if killer:
                        killer['score'] += 250
                        killer['xp'] += 100
                        if killer['xp'] >= killer['level'] * 150:
                            killer['level'] += 1
                            killer['maxHp'] += 20
                            killer['hp'] = killer['maxHp']
                break
                
        if b['life'] <= 0 and b in bullets:
            bullets.remove(b)

    # Check Orb Pickups
    for o in orbs[:]:
        for pid, p in players.items():
            if p['hp'] <= 0:
                continue
            if math.hypot(o['x'] - p['x'], o['y'] - p['y']) < 30:
                if o['type'] == 'xp':
                    p['xp'] += 25
                    p['score'] += 25
                elif o['type'] == 'health':
                    p['hp'] = min(p['maxHp'], p['hp'] + 35)
                elif o['type'] == 'speed':
                    p['speed'] += 1.0
                elif o['type'] == 'damage':
                    p['damageBoost'] = 2.0
                
                orbs.remove(o)
                orbs.append({
                    'id': f"orb_{now}",
                    'x': random.randint(100, MAP_WIDTH - 100),
                    'y': random.randint(100, MAP_HEIGHT - 100),
                    'type': random.choice(types)
                })
                break

class SiegeGameHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
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
            hero_class = data.get('class', 'Attacker')
            base_hp = 150 if hero_class == 'Defender' else (90 if hero_class == 'Scout' else 100)
            
            players[pid] = {
                'id': pid,
                'name': data.get('name', 'Hero')[:12],
                'class': hero_class,
                'x': random.randint(200, MAP_WIDTH - 200),
                'y': random.randint(200, MAP_HEIGHT - 200),
                'angle': 0,
                'hp': base_hp,
                'maxHp': base_hp,
                'level': 1,
                'xp': 0,
                'score': 0,
                'speed': 4 if hero_class == 'Defender' else (7 if hero_class == 'Scout' else 5),
                'shield': True,
                'shieldEnd': now + 3.0,
                'damageBoost': 1.0,
                'lastActive': now
            }
            response = {
                'id': pid, 
                'mapWidth': MAP_WIDTH, 
                'mapHeight': MAP_HEIGHT,
                'players': players,
                'orbs': orbs
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
                            'x': p['x'],
                            'y': p['y'],
                            'vx': math.cos(angle) * 14,
                            'vy': math.sin(angle) * 14,
                            'damage': 15 * p['damageBoost'],
                            'life': 50
                        })

            for key, player in list(players.items()):
                if now - player.get('lastActive', 0) > 5.0:
                    del players[key]

            response = {
                'players': players,
                'bullets': bullets,
                'orbs': orbs
            }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

if __name__ == "__main__":
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))

    server = HTTPServer((host, port), SiegeGameHandler)
    print(f"Starting server on http://{host}:{port}")
    server.serve_forever()
