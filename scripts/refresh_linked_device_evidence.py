"""Recheck saved source inventory against its PDF; update evidence only."""
import asyncio
import argparse
import json
from pathlib import Path
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
from app.models.project_file import ProjectFile
from app.models.ai_connection import AiConnection
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline


async def refresh(project_id):
    import fitz
    from PIL import Image
    logging.disable(logging.CRITICAL)
    out = Path(__file__).resolve().parents[2] / 'outputs' / 'linked-device-evidence'
    out.mkdir(parents=True, exist_ok=True)
    async with AsyncSessionLocal() as db:
        iteration = (await db.execute(select(AnalysisIteration).join(ConversationSession)
            .where(ConversationSession.project_id == project_id)
            .order_by(AnalysisIteration.created_at.desc()).limit(1))).scalar_one()
        devices = [ExtractedDeviceSchema.model_validate(row) for row in iteration.ai_parsed_devices]
        files = (await db.execute(select(ProjectFile).where(ProjectFile.project_id == project_id,
            ProjectFile.is_generated == False))).scalars().all()
        connections = (await db.execute(select(AiConnection).where(AiConnection.is_active == True,
            AiConnection.status == 'active').order_by(AiConnection.priority))).scalars().all()
        report = []
        for filename in dict.fromkeys(d.source_filename for d in devices if d.source_filename):
            source = next((f for f in files if f.filename == filename), None)
            if not source or not source.filename.lower().endswith('.pdf'):
                continue
            doc = fitz.open(source.file_path)
            for page_number in dict.fromkeys(d.source_page for d in devices if d.source_filename == filename):
                rows = [d for d in devices if d.source_filename == filename and d.source_page == page_number]
                page = doc[int(page_number) - 1]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                path = out / f'project-{project_id}-page-{page_number}.png'
                pix.save(path)
                inventory = [{'device_id': i, 'tag': d.tag, 'name': d.name, 'spec': d.spec,
                              'connected_load': d.connected_load, 'previous_box': d.box_2d} for i, d in enumerate(rows)]
                prompt = (
                    'Đối chiếu danh sách thiết bị với ảnh sơ đồ gốc. Không sửa danh mục, không suy từ tên đã gán. '
                    'Với từng device_id, tìm ký hiệu và toàn bộ nhãn thông số; box_2d bao đủ chúng, không ép vuông. '
                    'Lần theo đúng nhánh/dây để xác định nhãn tải. Trả riêng load_box_2d bao đủ nhãn tải, '
                    'load_label nguyên văn và relationship_evidence một câu nêu tag/nhánh nguồn nối tới tải đó. '
                    'Chỉ load_verified=true khi đọc rõ nhãn và kiểm tra đúng đường nối tới ký hiệu. '
                    'Không lấy thiết bị hoặc tải ở hàng kế bên; tên trong danh sách là giả thuyết cần kiểm chứng. '
                    'Nếu nhãn khác tên danh sách, ghi load_label đúng nguồn và load_verified=false. '
                    'Không đọc được/không chứng minh quan hệ thì không đoán. '
                    'JSON {"boxes":[{"device_id":0,"verified":true,"box_2d":[ymin,xmin,ymax,xmax],'
                    '"load_verified":true,"load_box_2d":[ymin,xmin,ymax,xmax],"load_label":"",'
                    '"relationship_evidence":""}]}; tọa độ 0..1000 theo toàn ảnh.\n'
                    + json.dumps(inventory, ensure_ascii=False))
                print(f'Verifying page {page_number}: {len(rows)} devices', flush=True)
                answer, _ = await ConnectionPoolService.call_with_fallback(db=db, connections=connections,
                    call_fn=VisionAnalyzerService.analyze_image, image_path=str(path), prompt=prompt)
                payload = next((b for b in ResponseParserService.extract_json_blocks(answer)
                                if isinstance(b, dict) and isinstance(b.get('boxes'), list)), None)
                if payload is None:
                    raise ValueError('No verified device evidence returned')
                (out / f'project-{project_id}-page-{page_number}-verification.json').write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
                Pipeline._apply_verified_boxes(rows, payload)
                with Image.open(path) as image:
                    for device in rows:
                        images = Pipeline._linked_evidence_images(device, image)
                        if images:
                            device.evidence_images = images
                            device.evidence_image = images[0]['evidence_image']
                        report.append({'tag': device.tag, 'name': device.name, 'page': page_number,
                            'linked_images': len(images), 'region': device.evidence_region})
                print(f'Page {page_number}: {sum(bool(d.evidence_images) for d in rows)} linked pairs', flush=True)
            doc.close()
        if not report:
            raise ValueError('No source pages matched; evidence was not updated')
        iteration.ai_parsed_devices = [d.model_dump() for d in devices]
        await db.commit()
        (out / f'project-{project_id}-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        print(f'Updated evidence: iteration {iteration.iteration_number}, {len(devices)} devices', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', type=int, required=True)
    args = parser.parse_args()
    asyncio.run(refresh(args.project_id))
