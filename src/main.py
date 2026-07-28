import http.server
import json
import math
import os
import random
import threading
import time
import urllib.parse
import uuid

# World configuration & Spatial Grid Setup
WORLD_SIZE = 2500
GRID_SIZE = 50  # 50x50 units per tile coordinate grid
TICKS_PER_SECOND = 30
TICK_INTERVAL = 1.0 / TICKS_PER_SECOND

# Game State
gameState = {
    "players": {},
    "orbs": [],
    "structures": [],
    "projectiles": [],
}

# 20 Unique Buildable Structures (Categorized with resource costs and health pools)
STRUCTURE_TYPES = {
    # Defenses
    "Wood Wall": {"cost": 20, "hp": 150, "category": "Defenses"},
    "Stone Wall": {"cost": 40, "hp": 300, "category": "Defenses"},
    "Iron Wall": {"cost": 70, "hp": 600, "category": "Defenses"},
    "Gate": {"cost": 50, "hp": 250, "category": "Defenses"},
    "Vault": {"cost": 100, "hp": 1000, "category": "Defenses"},
    "Barbed Wire": {"cost": 30, "hp": 100, "category": "Defenses"},
    # Traps & Hazards
    "Spike Trap": {"cost": 25, "hp": 80, "category": "Traps & Hazards"},
    "Flame Trap": {"cost": 45, "hp": 120, "category": "Traps & Hazards"},
    "Ice Trap": {"cost": 40, "hp": 120, "category": "Traps & Hazards"},
    "Mine": {"cost": 35, "hp": 50, "category": "Traps & Hazards"},
    "Tesla Coil": {"cost": 90, "hp": 200, "category": "Traps & Hazards"},
    # Support & Utility
    "Healing Totem": {"cost": 60, "hp": 150, "category": "Support & Utility"},
    "Speed Pad": {"cost": 30, "hp": 100, "category": "Support & Utility"},
    "Shield Gen": {"cost": 80, "hp": 300, "category": "Support & Utility"},
    "Radar Tower": {"cost": 70, "hp": 200, "category": "Support & Utility"},
    "Bounce Pad": {"cost": 35, "hp": 100, "category": "Support & Utility"},
    "Ammo Station": {"cost": 50, "hp": 180, "category": "Support & Utility"},
    "Teleporter": {"cost": 120, "hp": 250, "category": "Support & Utility"},
    "Mortar": {"cost": 100, "hp": 220, "category": "Support & Utility"},
    "Mini Turret": {"cost": 85, "hp": 200, "category": "Support & Utility"},
}

lock = threading.Lock()


def init_orbs():
  with lock:
    gameState["orbs"] = []
    for _ in range(80):
      gameState["orbs"].append({
          "id": str(uuid.uuid4()),
          "x": random.randint(100, WORLD_SIZE - 100),
          "y": random.randint(100, WORLD_SIZE - 100),
          "xp": random.randint(10, 25),
      })


init_orbs()


def game_loop():
  """Authoritative backend loop tracking 30 ticks per second for vector physics

  and spatial collision checks.
  """
  while True:
    start_time = time.time()
    with lock:
      # Update Projectile Vectors & Collisions
      active_projectiles = []
      for proj in gameState["projectiles"]:
        proj["x"] += proj["vx"]
        proj["y"] += proj["vy"]
        proj["life"] -= 1

        if (
            proj["x"] < 0
            or proj["x"] > WORLD_SIZE
            or proj["y"] < 0
            or proj["y"] > WORLD_SIZE
            or proj["life"] <= 0
        ):
          continue

        hit = False
        for pid, player in list(gameState["players"].items()):
          if pid == proj["owner"]:
            continue
          dist = ((player["x"] - proj["x"]) ** 2 + (player["y"] - proj["y"]) ** 2) ** 0.5
          if dist < 24:
            damage = proj.get("damage", 15)
            player["hp"] -= damage
            hit = True

            # Instant Elimination Logic
            if player["hp"] <= 0:
              killer_id = proj["owner"]
              if killer_id in gameState["players"]:
                # Award scrap and score to victor
                gameState["players"][killer_id]["scrap"] += player.get(
                    "scrap", 50
                ) + (player["level"] * 15)
                gameState["players"][killer_id]["score"] += 500

              # Respawn eliminated player back to start conditions
              player["x"] = random.randint(300, WORLD_SIZE - 300)
              player["y"] = random.randint(300, WORLD_SIZE - 300)
              player["hp"] = player["maxHp"]
              player["scrap"] = 50
              player["level"] = 1
              player["xp"] = 0
            break

        if not hit:
          active_projectiles.append(proj)
      gameState["projectiles"] = active_projectiles

      # Replenish Orbs
      while len(gameState["orbs"]) < 80:
        gameState["orbs"].append({
            "id": str(uuid.uuid4()),
            "x": random.randint(50, WORLD_SIZE - 50),
            "y": random.randint(50, WORLD_SIZE - 50),
            "xp": random.randint(10, 25),
        })

    elapsed = time.time() - start_time
    time.sleep(max(0, TICK_INTERVAL - elapsed))


threading.Thread(target=game_loop, daemon=True).start()


class GameServer(http.server.BaseHTTPRequestHandler):

  def do_GET(self):
    parsed_path = urllib.parse.urlparse(self.path)
    if parsed_path.path == "/" or parsed_path.path == "/index.html":
      self.send_response(200)
      self.send_header("Content-Type", "text/html")
      self.end_headers()
      index_path = os.path.join(
          os.path.dirname(__file__), "public", "index.html"
      )
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
      with lock:
        self.wfile.write(json.dumps(gameState).encode("utf-8"))
    else:
      self.send_response(404)
      self.end_headers()

  def do_POST(self):
    content_length = int(self.headers.get("Content-Length", 0))
    try:
      data = json.loads(self.rfile.read(content_length).decode("utf-8"))
    except:
      data = {}

    parsed_path = urllib.parse.urlparse(self.path)

    with lock:
      if parsed_path.path == "/join":
        player_id = str(uuid.uuid4())
        gameState["players"][player_id] = {
            "id": player_id,
            "x": random.randint(400, WORLD_SIZE - 400),
            "y": random.randint(400, WORLD_SIZE - 400),
            "hp": 100,
            "maxHp": 100,
            "level": 1,
            "xp": 0,
            "scrap": 50,
            "score": 0,
        }
        self.send_json({"playerId": player_id})

      elif parsed_path.path == "/update":
        pid = data.get("id")
        if pid in gameState["players"]:
          p = gameState["players"][pid]
          p["x"] = max(0, min(WORLD_SIZE, data.get("x", p["x"])))
          p["y"] = max(0, min(WORLD_SIZE, data.get("y", p["y"])))

          # Orb collection & 20 Level Progression Scaling
          remaining_orbs = []
          for orb in gameState["orbs"]:
            dist = ((p["x"] - orb["x"]) ** 2 + (p["y"] - orb["y"]) ** 2) ** 0.5
            if dist < 35:
              p["xp"] += orb["xp"]
              p["scrap"] += 5
              required_xp = p["level"] * 120
              if p["xp"] >= required_xp and p["level"] < 20:
                p["level"] += 1
                p["maxHp"] += 25
                p["hp"] = p["maxHp"]
            else:
              remaining_orbs.append(orb)
          gameState["orbs"] = remaining_orbs

        self.send_json({"status": "success"})

      elif parsed_path.path == "/shoot":
        pid = data.get("playerId")
        angle = data.get("angle", 0)
        if pid in gameState["players"]:
          p = gameState["players"][pid]
          damage = 15 + (p["level"] * 3)
          speed = 18
          gameState["projectiles"].append({
              "id": str(uuid.uuid4()),
              "owner": pid,
              "x": p["x"],
              "y": p["y"],
              "vx": math.cos(angle) * speed,
              "vy": math.sin(angle) * speed,
              "damage": damage,
              "life": 45,
          })
        self.send_json({"status": "success"})

      elif parsed_path.path == "/build":
        pid = data.get("playerId")
        stype = data.get("type")
        x = data.get("x")
        y = data.get("y")

        if pid in gameState["players"] and stype in STRUCTURE_TYPES:
          p = gameState["players"][pid]
          cost = STRUCTURE_TYPES[stype]["cost"]
          if p["scrap"] >= cost:
            p["scrap"] -= cost
            # Grid snapping mechanism (GRID_SIZE alignment)
            grid_x = round(x / GRID_SIZE) * GRID_SIZE
            grid_y = round(y / GRID_SIZE) * GRID_SIZE
            gameState["structures"].append({
                "id": str(uuid.uuid4()),
                "owner": pid,
                "type": stype,
                "x": grid_x,
                "y": grid_y,
                "hp": STRUCTURE_TYPES[stype]["hp"],
                "maxHp": STRUCTURE_TYPES[stype]["hp"],
            })
            self.send_json({"status": "success", "built": True})
          else:
            self.send_json({"status": "error", "message": "Insufficient scrap"})
        else:
          self.send_json({"status": "error", "message": "Invalid build request"})
      else:
        self.send_response(404)
        self.end_headers()

  def send_json(self, data):
    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.end_headers()
    self.wfile.write(json.dumps(data).encode("utf-8"))


def run(server_class=http.server.HTTPServer, handler_class=GameServer, port=8000):
  server_address = ("", port)
  httpd = server_class(server_address, handler_class)
  print(f"Siege Attack backend server active on http://localhost:{port}")
  httpd.serve_forever()


if __name__ == "__main__":
  run()
