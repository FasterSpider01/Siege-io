from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import os
import uuid
import random

gameState = {
    "players": {},
    "orbs": [],
    "structures": []
}

for _ in range(60):
    gameState["orbs"].append({
        "id": str(uuid.uuid4()),
        "x": random.randint(100, 2400),
        "y": random.randint(100, 2400),
        "xp": 10
    })

class GameServer(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/" or parsed_path.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            index_path = os.path.join(os.path.dirname(__file__), "public", "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"index.html not found in src/public/")
        elif parsed_path.path == "/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(gameState).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode('utf-8'))
        except:
            data = {}

        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == "/join":
            player_id = str(uuid.uuid4())
            gameState["players"][player_id] = {
                "id": player_id,
                "x": random.randint(500, 2000),
                "y": random.randint(500, 2000),
                "hp": 100,
                "maxHp": 100,
                "level": 1,
                "xp": 0,
                "score": 0
            }
            self.send_json({"playerId": player_id})

        elif parsed_path.path == "/update":
            pid = data.get("id")
            if pid in gameState["players"]:
                p = gameState["players"][pid]
                p["x"] = data.get("x", p["x"])
                p["y"] = data.get("y", p["y"])
                
                remaining_orbs = []
                for orb in gameState["orbs"]:
                    dist = ((p["x"] - orb["x"])**2 + (p["y"] - orb["y"])**2)**0.5
                    if dist < 35:
                        p["xp"] += orb["xp"]
                        if p["xp"] >= p["level"] * 100 and p["level"] < 20:
                            p["level"] += 1
                            p["maxHp"] += 20
                            p["hp"] = p["maxHp"]
                    else:
                        remaining_orbs.append(orb)
                gameState["orbs"] = remaining_orbs
                
                while len(gameState["orbs"]) < 60:
                    gameState["orbs"].append({
                        "id": str(uuid.uuid4()),
                        "x": random.randint(100, 2400),
                        "y": random.randint(100, 2400),
                        "xp": 10
                    })

            self.send_json({"status": "success"})

        elif parsed_path.path == "/build":
            structure = data.get("structure")
            if structure:
                gameState["structures"].append(structure)
            self.send_json({"status": "success"})
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def run(server_class=HTTPServer, handler_class=GameServer, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Optimized Server running on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
