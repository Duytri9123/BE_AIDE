import asyncio
import httpx

async def check_server():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:8000/docs", timeout=5)
            print("Server /docs status:", resp.status_code)
    except Exception as e:
        print("Server error:", e)

if __name__ == "__main__":
    asyncio.run(check_server())
