import asyncio
import websockets
import json
import time

API_KEY = "leadgen_secure_2024_x8f9"
WS_URL = f"ws://127.0.0.1:8000/api/ws/discovery?api_key={API_KEY}"

async def simulate_user(user_id: int):
    print(f"[User {user_id}] Connecting...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print(f"[User {user_id}] Connected. Sending search criteria...")
            
            # Send search payload
            payload = {
                "company_type": f"marketing agency in sector {user_id}",
                "product_or_service": "digital marketing",
                "location": "London"
            }
            await websocket.send(json.dumps(payload))
            
            # Listen for messages
            start_time = time.time()
            message_count = 0
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                if data.get("type") == "ping":
                    continue
                
                message_count += 1
                
                if data.get("type") == "done" or data.get("type") == "error":
                    elapsed = time.time() - start_time
                    print(f"[User {user_id}] Finished! Status: {data.get('type')}. Received {message_count} messages in {elapsed:.1f}s")
                    break
                
                # Print periodic progress to show it's alive
                if message_count % 20 == 0:
                    print(f"[User {user_id}] Progress update: {data.get('message', '')[:50]}...")
                    
    except Exception as e:
        print(f"[User {user_id}] Error: {e}")

async def main():
    print("Starting Load Test: 10 Concurrent Users")
    
    # Spawn 10 concurrent WebSocket connections
    tasks = [simulate_user(i) for i in range(1, 11)]
    await asyncio.gather(*tasks)
    
    print("Load Test Complete!")

if __name__ == "__main__":
    asyncio.run(main())
