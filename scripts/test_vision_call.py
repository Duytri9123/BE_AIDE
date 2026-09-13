import asyncio, sys, json
sys.stdout.reconfigure(encoding="utf-8")

from app.db.session import AsyncSessionLocal
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.prompt_template_service import PromptTemplateService
from app.core.prompts import (
    PROMPT_TYPES,
    SLD_VISION_ANALYSIS_PROMPT,
    append_canonical_output_contract,
    append_completeness_review_instruction,
    append_user_notes,
)

async def main():
    async with AsyncSessionLocal() as db:
        all_connections = await ConnectionPoolService.get_ordered_connections(db)
        print(f"Total connections: {len(all_connections)}")
        for conn in all_connections:
            print(f"  - {conn.id}: {conn.name} ({conn.provider}) model={conn.selected_model} active={conn.is_active}")

        vision_template = await PromptTemplateService.get_active_content(
            db, PROMPT_TYPES["SLD_VISION"], SLD_VISION_ANALYSIS_PROMPT
        )
        vision_prompt = append_user_notes(
            vision_template, None,
            "ĐẶC BIỆT LƯU Ý VÀ TUÂN THỦ YÊU CẦU KỸ THUẬT / GHI CHÚ TỪ KHÁCH HÀNG:",
        )
        vision_prompt = append_completeness_review_instruction(vision_prompt)
        vision_prompt = append_canonical_output_contract(vision_prompt)

        image_path = "storage/projects/31/nguon.jpg"
        print(f"Testing image: {image_path}")

        try:
            ai_response, used_conn = await ConnectionPoolService.call_with_fallback(
                db=db,
                connections=all_connections,
                call_fn=VisionAnalyzerService.analyze_image,
                image_path=image_path,
                prompt=vision_prompt,
            )
            print(f"Success with connection: {used_conn.name} ({used_conn.provider}) model={used_conn.selected_model}")
            print(f"Response length: {len(ai_response)}")
            print("Response first 500 chars:\n", ai_response[:500])
            print("\nResponse last 500 chars:\n", ai_response[-500:])

            with open("scripts/last_ai_response.txt", "w", encoding="utf-8") as f:
                f.write(ai_response)

            parsed_devs = ResponseParserService.parse_device_list(ai_response)
            print(f"Parsed devices count: {len(parsed_devs)}")

            json_blocks = ResponseParserService.extract_json_blocks(ai_response)
            print(f"JSON blocks count: {len(json_blocks)}")
            for idx, blk in enumerate(json_blocks):
                if isinstance(blk, dict):
                    print(f"Block {idx} keys:", list(blk.keys()))
                    if "devices" in blk:
                        print(f"  devices count in block: {len(blk['devices'])}")
                    if "file_assessment" in blk:
                        print(f"  file_assessment: {blk['file_assessment']}")

        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
