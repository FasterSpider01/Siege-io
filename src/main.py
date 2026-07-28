import asyncio
import websockets

# Keep track of all connected client websockets
connected = set()

async def handler(websocket):
    connected.add(websocket)
    try:
        async for message in websocket:
            # Broadcast the received player data to all other connected clients
            for client in connected:
                if client != websocket:
                    await client.send(message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected.remove(websocket)

async def main():
    print("WebSocket server started on ws://localhost:8765")
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # Keep the server running

if __name__ == "__main__":
    asyncio.run(main())
