import asyncio
import json
import websockets

# Keep track of all connected clients
connected_clients = set()


async def handle_client(websocket):
  connected_clients.add(websocket)
  try:
    async for message in websocket:
      # Parse movement data from a client and broadcast to others
      data = json.loads(message)
      for client in connected_clients:
        if client != websocket:
          await client.send(json.dumps(data))
  except websockets.exceptions.ConnectionClosed:
    pass
  finally:
    connected_clients.remove(websocket)


async def main():
  print("Starting WebSocket server on ws://localhost:8765...")
  async with websockets.serve(handle_client, "localhost", 8765):
    await asyncio.Future()  # Run forever


if __name__ == "__main__":
  asyncio.run(main())
