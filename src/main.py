import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Dictionary to track active player coordinates in memory
players = {}


class GameServer(SimpleHTTPRequestHandler):

  def do_OPTIONS(self):
    # Handle CORS preflight requests from GitHub Pages
    self.send_response(200)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.end_headers()

  def do_POST(self):
    content_length = int(self.headers.get("Content-Length", 0))
    post_data = self.rfile.read(content_length)
    try:
      data = json.loads(post_data.decode("utf-8"))
      player_id = data.get("id")
      if player_id:
        players[player_id] = {
            "x": data.get("x", 0),
            "y": data.get("y", 0),
            "z": data.get("z", 0),
        }

      self.send_response(200)
      self.send_header("Access-Control-Allow-Origin", "*")
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
    except Exception as e:
      self.send_response(400)
      self.send_header("Access-Control-Allow-Origin", "*")
      self.end_headers()

  def do_GET(self):
    # Return all player coordinates to the client frontend
    self.send_response(200)
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(players).encode("utf-8"))


if __name__ == "__main__":
  host = os.environ.get("HOST", "0.0.0.0")
  port = int(os.environ.get("PORT", 8080))

  server = HTTPServer((host, port), GameServer)
  print(f"Starting Wasmer game server on http://{host}:{port}")
  server.serve_forever()
