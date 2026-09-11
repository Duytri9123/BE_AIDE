import asyncio
import httpx

async def test_admin_api():
    # Test through localhost:8000
    # Let's send a TestConnectionRequest with a dummy test or verify admin helpers directly
    from app.endpoints.admin_helpers import _test_gemini
    print("Testing _test_gemini with fallback cascade...")
    # Using the key from the earlier test
    from app.services.ai.vision_analyzer import VisionAnalyzerService
    print("All modules imported cleanly.")

if __name__ == "__main__":
    asyncio.run(test_admin_api())
