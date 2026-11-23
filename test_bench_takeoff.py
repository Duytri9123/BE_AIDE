"""Benchmark test script to evaluate takeoff performance and accuracy comparison."""
import asyncio
import time
import json
from pathlib import Path

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.services.ai.scoped_takeoff import extract_confirmed_panels


async def main():
    print("=" * 70)
    print("🚀 BẮT ĐẦU CHẠY BENCHMARK BÓC TÁCH TỦ DB-HEY (PROJECT 49)")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        user = await db.get(User, 9)
        project = await db.get(Project, 49)
        if not project:
            print("❌ Không tìm thấy Project 49")
            return

        from sqlalchemy import select
        res = await db.execute(select(ProjectFile).where(ProjectFile.project_id == 49))
        file = res.scalars().first()
        if not file:
            print("❌ Không tìm thấy file trong Project 49")
            return

        print(f"📁 Tệp: {file.filename} (ID: {file.id})")
        print(f"👤 Người dùng: ID={user.id} ({user.email})")

        panels = [{
            "panel_code": "DB-HEY",
            "panel_name": "Tủ DB-HEY",
            "source_file_id": file.id,
            "source_page": 11,
            "source_region": [0.088, 0.272, 0.812, 0.704]
        }]

        t_start = time.perf_counter()

        results = await extract_confirmed_panels(
            db=db,
            project_id=49,
            panels=panels,
            message="Bóc tách thiết bị điện trong bản vẽ HEY PELO HA LONG MEPF_06.03.2026.pdf"
        )

        t_total = time.perf_counter() - t_start

        print("\n" + "=" * 70)
        print(f"🏁 HOÀN TẤT BÓC TÁCH TRONG: {t_total:.1f} GIÂY ({t_total/60:.2f} PHÚT)")
        print(f"📊 Tổng số thiết bị trích xuất: {len(results)}")
        print("=" * 70)

        # Kiểm tra chi tiết các thiết bị đặc thù
        rcbo_count = 0
        timer_count = 0
        shunt_count = 0
        with_candidates_count = 0

        for i, d in enumerate(results):
            name = d.get('name') or d.get('category') or ''
            spec = d.get('spec') or ''
            tag = d.get('tag') or d.get('location') or ''
            cands = d.get('catalog_candidates') or {}
            c_brands = list(cands.keys())

            if cands:
                with_candidates_count += 1
            if 'RCBO' in name.upper() or 'RCBO' in spec.upper():
                rcbo_count += 1
            if 'TIMER' in name.upper() or 'TIMER' in spec.upper():
                timer_count += 1
            if 'CUỘN CẮT' in name or 'SHUNT' in name.upper() or 'S/T' in tag:
                shunt_count += 1

            if i < 15 or 'TIMER' in name.upper() or 'RCBO' in name.upper() or 'CUỘN CẮT' in name:
                print(f"[{i+1:2d}] {name} ({tag}) | {spec} | Gợi ý hãng: {c_brands[:3]}")

        print("\n" + "-" * 70)
        print(f"✅ Thiết bị có gợi ý mã (catalog_candidates): {with_candidates_count}/{len(results)}")
        print(f"✅ RCBO phát hiện: {rcbo_count}")
        print(f"✅ Timer phát hiện: {timer_count}")
        print(f"✅ Cuộn cắt Shunt trip phát hiện: {shunt_count}")
        print("-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
