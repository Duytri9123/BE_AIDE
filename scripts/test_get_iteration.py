import asyncio, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from app.core.security import create_access_token

async def test():
    token = create_access_token(subject="9")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8000/api/v1/analyze/iteration/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        print("Status code:", resp.status_code)
        if resp.status_code != 200:
            print("Error:", resp.text)
        else:
            data = resp.json()
            print("Session ID:", data.get("session_id"))
            print("Iteration number:", data.get("iteration_number"))
            print("Devices count:", len(data.get("devices", [])))

asyncio.run(test())
