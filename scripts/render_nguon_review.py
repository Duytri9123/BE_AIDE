"""Manually reviewed demonstration overlay for the repository's nguon.jpg sample."""

import base64
import json
from pathlib import Path
from types import SimpleNamespace

from app.services.ai.evidence_overview import render_evidence_overview


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "BE_AIDE" / "storage" / "projects" / "1" / "nguon.jpg"
OUTPUT = ROOT / "artifacts" / "nguon-vi-tri-da-doc.jpg"
LEGEND = ROOT / "artifacts" / "nguon-vi-tri-da-doc.json"


def px_box(x1, y1, x2, y2):
    return [round(y1 * 1000 / 777), round(x1 * 1000 / 1000),
            round(y2 * 1000 / 777), round(x2 * 1000 / 1000)]


observed = [
    ("NGUỒN", "Nguồn từ tủ trạm biến áp", (271, 61, 540, 107)),
    ("TỦ", "Thông tin tủ 1200×800×400", (102, 108, 221, 197)),
    ("CT", "3XCT 63/5", (491, 107, 558, 148)),
    ("AS", "Công tắc chọn dòng", (605, 112, 642, 144)),
    ("A", "Ampe kế 0–50A", (645, 112, 698, 144)),
    ("QF", "MCCB tổng 3P 63A 18kA", (488, 149, 543, 211)),
    ("2A", "Bảo vệ mạch đo", (562, 149, 619, 173)),
    ("R", "Đèn báo pha R", (627, 150, 654, 174)),
    ("Y", "Đèn báo pha Y", (652, 150, 679, 174)),
    ("B", "Đèn báo pha B", (677, 150, 706, 174)),
    ("VS", "Công tắc chọn áp", (601, 180, 644, 211)),
    ("V", "Vôn kế 0–500V", (647, 180, 704, 213)),
    ("PE", "Ký hiệu nối đất", (965, 235, 997, 288)),
    ("THANH CÁI", "Thanh phân phối 63A", (126, 209, 958, 222)),
]
for index in range(28):
    centre = 135 + index * 30
    observed.append((f"M{index + 1}", f"Lộ M{index + 1}: CB, cáp và phụ tải",
                     (centre - 14, 210, centre + 14, 678)))

devices = [SimpleNamespace(tag=tag, name=name, box_2d=px_box(*box))
           for tag, name, box in observed]
result = render_evidence_overview(SOURCE, devices)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_bytes(base64.b64decode(result["image"].split(",", 1)[1]))
LEGEND.write_text(json.dumps({"source": str(SOURCE), "review_method": "manual",
                              "note": "Vị trí trên ảnh mẫu; không thay cho vùng AI được xác minh trong lần chạy mới.",
                              "legend": result["legend"]}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{result['marked_count']} positions -> {OUTPUT}")
