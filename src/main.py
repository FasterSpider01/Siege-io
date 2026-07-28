
import http.server
import json
import math
import os
import random
import threading
import time
import uuid
import urllib.parse

# =========================================================
# CONFIGURATION
# =========================================================

WORLD_SIZE = 2500
TILE_SIZE = 50

GRID_WIDTH = WORLD_SIZE // TILE_SIZE
TICK_RATE = 60
TICK_TIME = 1 / TICK_RATE


# =========================================================
# GAME STATE
# =========================================================

game = {
    "players": {},
    "projectiles": [],
    "structures": [],
    "orbs": [],
    "scrap": [],
    "effects": []
}

lock = threading.Lock()


# =========================================================
# SPATIAL GRID
# =========================================================

class SpatialGrid:

    def __init__(self):
        self.cells = {}

    def key(self, x, y):
        return (
            int(x // TILE_SIZE),
            int(y // TILE_SIZE)
        )

    def clear(self):
        self.cells.clear()

    def add(self, entity):
        cell = self.key(entity["x"], entity["y"])

        if cell not in self.cells:
            self.cells[cell] = []

        self.cells[cell].append(entity)

    def nearby(self, x, y, radius=100):

        cx, cy = self.key(x, y)

        results = []

        tiles = int(radius / TILE_SIZE) + 1

        for gx in range(cx - tiles, cx + tiles + 1):
            for gy in range(cy - tiles, cy + tiles + 1):

                if (gx, gy) in self.cells:
                    results.extend(
                        self.cells[(gx, gy)]
                    )

        return results


player_grid = SpatialGrid()
structure_grid = SpatialGrid()


# =========================================================
# BUILDINGS
# =========================================================

STRUCTURES = {

    # defenses
    "Wood Wall": {
        "cost":20,
        "hp":150
    },

    "Stone Wall":{
        "cost":40,
        "hp":350
    },

    "Iron Wall":{
        "cost":70,
        "hp":700
    },

    "Gate":{
        "cost":50,
        "hp":300
    },

    "Vault":{
        "cost":120,
        "hp":1200
    },

    "Barbed Wire":{
        "cost":30,
        "hp":100
    },


    # traps

    "Spike Trap":{
        "cost":25,
        "hp":100
    },

    "Flame Trap":{
        "cost":45,
        "hp":150
    },

    "Ice Trap":{
        "cost":40,
        "hp":150
    },

    "Mine":{
        "cost":35,
        "hp":80
    },

    "Tesla Coil":{
        "cost":90,
        "hp":250
    },


    # utilities

    "Healing Totem":{
        "cost":60,
        "hp":200
    },

    "Speed Pad":{
        "cost":30,
        "hp":100
    },

    "Shield Gen":{
        "cost":80,
        "hp":350
    },

    "Radar Tower":{
        "cost":70,
        "hp":250
    },

    "Bounce Pad":{
        "cost":35,
        "hp":120
    },

    "Ammo Station":{
        "cost":50,
        "hp":200
    },

    "Teleporter":{
        "cost":120,
        "hp":300
    },

    "Mortar":{
        "cost":100,
        "hp":250
    },

    "Mini Turret":{
        "cost":85,
        "hp":220
    }
}



# =========================================================
# PLAYER CREATION
# =========================================================


def create_player():

    return {

        "id":str(uuid.uuid4()),

        "x":random.randint(
            200,
            WORLD_SIZE-200
        ),

        "y":random.randint(
            200,
            WORLD_SIZE-200
        ),


        "vx":0,
        "vy":0,


        "hp":100,
        "max_hp":100,


        "level":1,
        "xp":0,


        "speed":5,
        "damage":15,


        "scrap":50,

        "score":0
    }



# =========================================================
# LEVEL SYSTEM
# =========================================================


def add_xp(player, amount):

    player["xp"] += amount


    needed = player["level"] * 100


    while (
        player["xp"] >= needed
        and player["level"] < 20
    ):

        player["xp"] -= needed

        player["level"] += 1


        # scaling

        player["max_hp"] += 25

        player["hp"] = player["max_hp"]

        player["speed"] += .15

        player["damage"] += 3


        needed = player["level"] * 100



# =========================================================
# ORBS
# =========================================================


def spawn_orb():

    return {

        "id":str(uuid.uuid4()),

        "x":random.randint(
            50,
            WORLD_SIZE-50
        ),

        "y":random.randint(
            50,
            WORLD_SIZE-50
        ),

        "xp":random.randint(
            10,
            30
        )
    }



def refill_orbs():

    while len(game["orbs"]) < 100:
        game["orbs"].append(
            spawn_orb()
        )



# =========================================================
# SCRAP DROPS
# =========================================================


def drop_scrap(x,y,amount):

    for _ in range(amount):

        game["scrap"].append({

            "x":x+random.randint(-30,30),

            "y":y+random.randint(-30,30),

            "value":1
        })



# =========================================================
# RESET GRIDS
# =========================================================


def rebuild_grids():

    player_grid.clear()
    structure_grid.clear()


    for p in game["players"].values():
        player_grid.add(p)


    for s in game["structures"]:
        structure_grid.add(s)



# =========================================================
# STARTUP WORLD
# =========================================================


for _ in range(100):

    game["orbs"].append(
        spawn_orb()
    )


# =========================================================
# COMBAT CONSTANTS
# =========================================================

PROJECTILE_SPEED = 20
PROJECTILE_LIFE = 90

PLAYER_RADIUS = 22
STRUCTURE_RADIUS = 25



# =========================================================
# PROJECTILES
# =========================================================


def create_projectile(player, angle):

    return {

        "id": str(uuid.uuid4()),

        "owner": player["id"],

        "x": player["x"],

        "y": player["y"],


        "vx": math.cos(angle) * PROJECTILE_SPEED,

        "vy": math.sin(angle) * PROJECTILE_SPEED,


        "damage": player["damage"],

        "life": PROJECTILE_LIFE
    }



# =========================================================
# DISTANCE CHECK
# =========================================================


def distance(a,b):

    return math.sqrt(
        (a["x"]-b["x"])**2 +
        (a["y"]-b["y"])**2
    )



# =========================================================
# PLAYER DAMAGE
# =========================================================


def damage_player(target, damage, attacker=None):

    target["hp"] -= damage


    if target["hp"] <= 0:


        if attacker:

            attacker["score"] += 500

            attacker["scrap"] += (
                target["scrap"]
            )


        drop_scrap(
            target["x"],
            target["y"],
            10
        )


        respawn_player(target)



# =========================================================
# RESPAWN
# =========================================================


def respawn_player(player):

    player["x"] = random.randint(
        200,
        WORLD_SIZE-200
    )

    player["y"] = random.randint(
        200,
        WORLD_SIZE-200
    )


    player["hp"] = player["max_hp"]

    player["level"] = 1

    player["xp"] = 0

    player["damage"] = 15

    player["speed"] = 5



# =========================================================
# STRUCTURE DAMAGE
# =========================================================


def damage_structure(structure, damage):

    structure["hp"] -= damage


    if structure["hp"] <= 0:

        if structure in game["structures"]:

            game["structures"].remove(
                structure
            )


        game["effects"].append({

            "type":"destroy",

            "x":structure["x"],

            "y":structure["y"]

        })



# =========================================================
# PROJECTILE UPDATE
# =========================================================


def update_projectiles():

    alive = []


    for proj in game["projectiles"]:


        proj["x"] += proj["vx"]

        proj["y"] += proj["vy"]


        proj["life"] -= 1


        if proj["life"] <= 0:
            continue


        if (
            proj["x"] < 0 or
            proj["y"] < 0 or
            proj["x"] > WORLD_SIZE or
            proj["y"] > WORLD_SIZE
        ):
            continue



        hit = False



        # player collision

        for player in player_grid.nearby(
            proj["x"],
            proj["y"],
            50
        ):


            if player["id"] == proj["owner"]:
                continue


            if distance(
                proj,
                player
            ) < PLAYER_RADIUS:


                owner = game["players"].get(
                    proj["owner"]
                )


                damage_player(
                    player,
                    proj["damage"],
                    owner
                )


                hit = True

                break



        if hit:
            continue



        # structure collision

        for structure in structure_grid.nearby(
            proj["x"],
            proj["y"],
            50
        ):


            if distance(
                proj,
                structure
            ) < STRUCTURE_RADIUS:


                damage_structure(
                    structure,
                    proj["damage"]
                )


                hit=True

                break



        if not hit:

            alive.append(
                proj
            )


    game["projectiles"] = alive



# =========================================================
# ORB + SCRAP COLLECTION
# =========================================================


def update_resources():

    remove=[]


    for player in game["players"].values():


        for orb in game["orbs"]:

            if distance(
                player,
                orb
            ) < 35:


                add_xp(
                    player,
                    orb["xp"]
                )


                remove.append(
                    orb
                )



        for item in game["scrap"]:

            if distance(
                player,
                item
            ) < 30:


                player["scrap"] += item["value"]

                remove.append(
                    item
                )



    for item in remove:

        if item in game["orbs"]:
            game["orbs"].remove(item)


        if item in game["scrap"]:
            game["scrap"].remove(item)



    refill_orbs()



# =========================================================
# BUILDING
# =========================================================


def snap(value):

    return round(
        value / TILE_SIZE
    ) * TILE_SIZE



def build_structure(
    player,
    structure_type,
    x,
    y
):

    if structure_type not in STRUCTURES:
        return False


    info = STRUCTURES[
        structure_type
    ]


    if player["scrap"] < info["cost"]:
        return False



    player["scrap"] -= info["cost"]



    structure={

        "id":str(uuid.uuid4()),

        "owner":player["id"],

        "type":structure_type,


        "x":snap(x),

        "y":snap(y),


        "hp":info["hp"],

        "max_hp":info["hp"]
    }


    game["structures"].append(
        structure
    )


    return True



# =========================================================
# PLAYER MOVEMENT
# =========================================================


def update_players():

    for player in game["players"].values():


        player["x"] += (
            player["vx"] *
            player["speed"]
        )


        player["y"] += (
            player["vy"] *
            player["speed"]
        )



        player["x"] = max(
            0,
            min(
                WORLD_SIZE,
                player["x"]
            )
        )


        player["y"] = max(
            0,
            min(
                WORLD_SIZE,
                player["y"]
            )
        )



# =========================================================
# MAIN GAME TICK
# =========================================================


def update_game():

    rebuild_grids()

    update_players()

    update_resources()

    update_projectiles()




# =========================================================
# HTTP SERVER
# =========================================================


class SiegeHandler(http.server.BaseHTTPRequestHandler):


    def send_json(self,data):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.end_headers()


        self.wfile.write(
            json.dumps(data).encode()
        )



    def do_GET(self):

        path = urllib.parse.urlparse(
            self.path
        ).path



        # Serve game client

        if path == "/" or path == "/index.html":

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html"
            )

            self.end_headers()


            file = os.path.join(
                os.path.dirname(__file__),
                "public",
                "index.html"
            )


            if os.path.exists(file):

                with open(
                    file,
                    "rb"
                ) as f:

                    self.wfile.write(
                        f.read()
                    )

            else:

                self.wfile.write(
                    b"Missing public/index.html"
                )



        # World snapshot

        elif path == "/state":

            with lock:

                self.send_json({

                    "players":
                    list(
                        game["players"].values()
                    ),

                    "structures":
                    game["structures"],

                    "projectiles":
                    game["projectiles"],

                    "orbs":
                    game["orbs"],

                    "scrap":
                    game["scrap"]

                })


        else:

            self.send_response(404)

            self.end_headers()



    def do_POST(self):

        length=int(
            self.headers.get(
                "Content-Length",
                0
            )
        )


        try:

            data=json.loads(
                self.rfile.read(length)
                .decode()
            )

        except:

            data={}



        path=urllib.parse.urlparse(
            self.path
        ).path



        with lock:


            # =====================================
            # JOIN GAME
            # =====================================

            if path=="/join":


                player=create_player()


                pid=player["id"]


                game["players"][pid]=player


                self.send_json({

                    "id":pid,

                    "player":player

                })



            # =====================================
            # PLAYER MOVEMENT
            # =====================================

            elif path=="/update":


                pid=data.get(
                    "id"
                )


                player=game["players"].get(
                    pid
                )


                if player:


                    player["vx"]=float(
                        data.get(
                            "vx",
                            0
                        )
                    )


                    player["vy"]=float(
                        data.get(
                            "vy",
                            0
                        )
                    )



                self.send_json(
                    {
                        "ok":True
                    }
                )



            # =====================================
            # SHOOTING
            # =====================================

            elif path=="/shoot":


                pid=data.get(
                    "id"
                )


                angle=float(
                    data.get(
                        "angle",
                        0
                    )
                )


                player=game["players"].get(
                    pid
                )


                if player:

                    game["projectiles"].append(
                        create_projectile(
                            player,
                            angle
                        )
                    )



                self.send_json(
                    {
                        "ok":True
                    }
                )



            # =====================================
            # BUILDING
            # =====================================

            elif path=="/build":


                pid=data.get(
                    "id"
                )


                player=game["players"].get(
                    pid
                )


                if player:


                    success=build_structure(

                        player,

                        data.get(
                            "type"
                        ),

                        data.get(
                            "x",
                            player["x"]
                        ),

                        data.get(
                            "y",
                            player["y"]
                        )
                    )


                    self.send_json({

                        "built":success

                    })


                else:

                    self.send_json({

                        "built":False

                    })



            # =====================================
            # REMOVE PLAYER
            # =====================================

            elif path=="/leave":


                pid=data.get(
                    "id"
                )


                if pid in game["players"]:

                    del game["players"][pid]


                self.send_json(
                    {
                        "ok":True
                    }
                )


            else:

                self.send_json(
                    {
                        "error":"unknown endpoint"
                    }
                )



# =========================================================
# GAME THREAD
# =========================================================


def server_loop():


    while True:


        start=time.time()


        with lock:

            update_game()


        elapsed=time.time()-start


        wait=TICK_TIME-elapsed


        if wait>0:

            time.sleep(
                wait
            )



# =========================================================
# START SERVER
# =========================================================


def run():

    threading.Thread(
        target=server_loop,
        daemon=True
    ).start()



    server=http.server.ThreadingHTTPServer(

        (
            "",
            8000
        ),

        SiegeHandler

    )


    print(
        "Siege Attack running on http://localhost:8000"
    )


    server.serve_forever()



if __name__=="__main__":

    run()

