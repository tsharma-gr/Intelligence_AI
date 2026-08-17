import asyncio
import sys
import uvicorn

if sys.platform == "win32":
    # Force the ProactorEventLoop before any other async operations or server startup
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    print("Starting Company Intelligence AI server with ProactorEventLoop (Playwright compatible)...")
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000)
