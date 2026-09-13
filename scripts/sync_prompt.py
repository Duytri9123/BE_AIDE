import asyncio, sys
sys.stdout.reconfigure(encoding="utf-8")

from app.db.session import AsyncSessionLocal
from app.models.prompt_template import PromptTemplate
from app.core.prompts import PROMPT_TYPES, SLD_VISION_ANALYSIS_PROMPT
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(PromptTemplate).where(PromptTemplate.type == PROMPT_TYPES["SLD_VISION"])
        )
        template = res.scalar_one_or_none()
        if template:
            template.content = SLD_VISION_ANALYSIS_PROMPT
            print(f"Updated prompt template id={template.id}, length={len(template.content)}")
            await db.commit()
        else:
            print("Template not found!")

if __name__ == "__main__":
    asyncio.run(main())
