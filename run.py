import uvicorn
import asyncio
import sys

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000)
