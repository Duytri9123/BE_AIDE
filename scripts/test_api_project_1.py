import asyncio, sys, httpx
sys.stdout.reconfigure(encoding="utf-8")
from app.core.security import create_access_token

async def test():
    token = create_access_token(subject="9")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://localhost:8000/api/v1/projects/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        print("Status code:", resp.status_code)
        print("Project 1 details:", resp.text)

asyncio.run(test())
