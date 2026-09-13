import asyncio, sys, httpx, json
sys.stdout.reconfigure(encoding="utf-8")
from app.core.security import create_access_token

async def test():
    token = create_access_token(subject="9")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "project_id": 1,
        "file_id": 1,
        "is_new_session": False,
        "fallback_to_standard_template": False,
        "user_prompt": None,
    }
    print("Calling /api/v1/analyze/stream on PID 4176...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/analyze/stream",
            headers=headers,
            json=payload,
        ) as resp:
            print("Status code:", resp.status_code)
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    data = json.loads(data_str)
                    dtype = data.get("type") or data.get("stage")
                    title = data.get("title")
                    print(f"SSE: [{dtype}] {title}")
                    if dtype == "complete":
                        result = data.get("result", {})
                        devs = result.get("devices", [])
                        print(f"COMPLETE! Total devices: {len(devs)}")
                        warnings = result.get("warnings", [])
                        print(f"Warnings: {warnings}")
                    elif dtype == "error":
                        print(f"ERROR: {data}")

asyncio.run(test())
