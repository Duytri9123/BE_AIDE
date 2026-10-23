"""Create a normal, isolated audit user/project in the application's actual database."""
import asyncio
import json
import os
from pathlib import Path
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.project import Project
from app.models.ai_connection import AiConnection


async def main():
    async with AsyncSessionLocal() as db:
        email = 'cad-agent-audit-20261023-01@tests.elquote.local'
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            user = User(email=email, name='Kiểm thử CAD Agent 23/10/2026',
                hashed_password=get_password_hash(os.environ['CAD_AUDIT_PASSWORD']), status='active', role='user')
            db.add(user)
            await db.flush()
        project = (await db.execute(select(Project).where(Project.user_id == user.id,
            Project.name == 'Kiểm thử tích hợp CAD Agent 23/10/2026'))).scalar_one_or_none()
        if not project:
            project = Project(user_id=user.id, name='Kiểm thử tích hợp CAD Agent 23/10/2026', category='CAD integration test')
            db.add(project)
        await db.commit()
        connections = (await db.execute(select(AiConnection.provider, AiConnection.status, AiConnection.is_active))).all()
        result = {'user_id': user.id, 'project_id': project.id,
            'connections': [{'provider': p, 'status': s, 'active': a} for p, s, a in connections]}
        path = Path('../AIDE/outputs/package-audit-20261023/system-fixture.json')
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    asyncio.run(main())
