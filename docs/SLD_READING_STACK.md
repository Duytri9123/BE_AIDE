# Đọc sơ đồ nguyên lý và sơ đồ một sợi từ ảnh, PDF, CAD

Đối chiếu GitHub ngày 05/11/2026. Đây là lựa chọn theo chức năng và mã nguồn
công bố; chưa phải chứng nhận độ chính xác trên bộ bản vẽ thực tế của hệ thống.

## Bộ công cụ cốt lõi nên giữ

| Repo chính thức | Vai trò | Giới hạn cần hiểu |
| --- | --- | --- |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | Đọc chữ, tọa độ, đường nét PDF; render trang và crop | Đường nét PDF không tự mang ý nghĩa dây điện; khung tên, bảng và nét ký hiệu cũng là đường nét. Tọa độ PDF không phải kích thước thực CAD. |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Đọc tag, thông số, ghi chú trong ảnh/PDF scan | OCR không xác nhận loại ký hiệu, số lượng thiết bị hoặc hai nét có nối điện với nhau. |
| [ezdxf](https://github.com/mozman/ezdxf) | Đọc DXF: entity, block, attribute, layer, tọa độ | Block bị explode và tên block chung vẫn cần phân loại bằng hình học/ảnh. DWG phải chuyển đổi bằng công cụ phù hợp. |
| [LibreDWG](https://github.com/LibreDWG/libredwg) | Đọc/chuyển DWG sang DXF/JSON; có bản build Windows | Kiểm tra phiên bản DWG, dynamic block, text tiếng Việt và hình render sau chuyển. Không tự hiểu mạch điện. |
| [OpenCV](https://github.com/opencv/opencv) | Tách nét, tìm junction dot, skeleton, xử lý ảnh | Phải phân biệt đường dây, nét ký hiệu, khung và giao cắt; cần kiểm tra trên ảnh thật. |
| [NetworkX](https://github.com/networkx/networkx) | Biểu diễn graph thiết bị–đầu cực–net; truy vết quan hệ | Phân tích chỉ đúng khi graph đầu vào đúng. Không tự nhận diện ảnh hoặc suy ra logic vận hành bị thiếu. |

Hệ thống hiện có PyMuPDF, ezdxf, OpenCV và NetworkX trong dependencies backend.
PaddleOCR chạy riêng với Python 3.13 để tương thích PaddlePaddle; xem
[drawing-reader.md](drawing-reader.md). Không cần cài thêm một bộ OCR tổng quát
khác chỉ để nhân đôi chức năng hiện có.

## Repo sát bài toán sơ đồ điện để tham khảo thêm

### 1. circuit-vision — thử nghiệm nhận diện ký hiệu và liên kết

Repo: https://github.com/zakaneki/circuit-vision

README và `predictor.py` có pipeline YOLO OBB, OCR, tách dây, junction và phân
tích connectivity; repo có `best.pt`. `data.yaml` công bố đúng **4 lớp**:
Transformer, Circuit Breaker, Switch, MV Line.

Đây là hướng tham khảo gần SLD hơn eDOCr2. Chưa đủ để dùng ngay cho toàn bộ
tủ hạ thế có MCB/MCCB/ACB, RCBO/RCCB, CT, cầu chì, đồng hồ, AS/VS, contactor,
timer và mạch điều khiển. Cần dữ liệu gán nhãn của chính người dùng, kiểm tra
quyền sử dụng mã/model và đánh giá cả nhận diện lẫn liên kết trước khi tích hợp.
Không tự động tải và chạy checkpoint từ repo trong lần dọn hệ thống này.

### 2. electrical-symbol-library — kiến thức tham chiếu cho agent

Repo: https://github.com/elora-grid/electrical-symbol-library

Cung cấp records JSON, giải thích ký hiệu, chức năng bảo vệ, ngữ cảnh IEC và
ANSI/IEEE, SVG và DXF minh họa. Phù hợp làm nguồn tra cứu để agent giải thích
ký hiệu và phân biệt chức năng thiết bị.

Theo chính README, đây là tài liệu minh họa độc lập; không phải ấn phẩm tiêu
chuẩn chính thức, bộ glyph được chứng nhận hoặc footprint nhà sản xuất. Không
thay thế thư viện hình học/thiết bị thật của dự án. Dữ liệu/minh họa có yêu cầu
ghi công CC BY 4.0; code/schema dùng MIT.

### 3. SchematicNetlist — tham khảo trích graph từ PDF

Repo: https://github.com/sphrd/SchematicNetlist

Đọc schematic PDF thành components, pins, nets và JSON/netlist. Mã mô tả xử lý
vector, nhãn xuyên trang và fallback OpenCV/Tesseract cho trang scan. Hướng
chính là sơ đồ điện tử/ECAD và HSPICE; chưa có bằng chứng đã phù hợp với toàn
bộ quy ước sơ đồ một sợi của tủ điện Việt Nam.

Phù hợp nghiên cứu cách khôi phục topology, đối chiếu pin–net và xuất cảnh báo;
không coi số liệu từ README là kết quả đánh giá của hệ thống này.

## Cách ghép để agent đọc và giải thích nguyên lý

1. Phân loại nguồn: ảnh/scan, PDF vector, DXF hoặc DWG. Giữ file gốc và số trang.
2. Lấy dữ liệu có cấu trúc trước: entity/block/attribute của CAD; chữ và vector
   của PDF. Dùng OCR bổ sung khi thiếu chữ hoặc chữ chỉ còn là hình học.
3. Nhận diện ký hiệu riêng với OCR nhãn. Gắn nhãn theo vị trí và đường dẫn
   bằng chứng, giữ confidence và phần không đọc rõ.
4. Dựng graph: thiết bị, đầu cực, thanh cái, net, nguồn, tải, tham chiếu xuyên
   trang. Không mặc định mọi đường giao nhau đều nối điện.
5. Cho agent giải thích đường cấp điện, đo lường, bảo vệ, liên động và trình tự
   hoạt động dựa trên graph đã đối chiếu. Trạng thái tiếp điểm, nguồn điều khiển
   hoặc liên động chưa đủ dữ liệu phải được ghi là chưa xác định.
6. Mỗi kết luận quan trọng cần file/trang, bbox hoặc entity handle. Đọc ký hiệu
   đúng chưa đủ để khẳng định đã hiểu đúng nguyên lý.

## Không ưu tiên cho bài toán này

* [eDOCr2](https://github.com/javvi51/edocr2) tập trung bản vẽ cơ khí/sản xuất;
  có thể hỗ trợ OCR nhưng không phải bộ đọc SLD chuyên biệt.
* [PCBnet](https://github.com/ECNUACRush/PCBnet) công bố dataset/phương pháp
  PCB schematic; README hiện nói chưa phát hành mã nguồn. Không phải engine
  có thể cài vào production ngay.
* Docling/MinerU hữu ích cho tài liệu và bảng nhiều trang nhưng không tự giải
  quyết việc nối dây, junction, tiếp điểm và logic vận hành.

Ưu tiên đề xuất: hoàn thiện **PyMuPDF + PaddleOCR + ezdxf/LibreDWG + graph
điện** hiện có; dùng các repo chuyên biệt làm nguồn tham khảo có đánh giá,
không cài đồng thời nhiều pipeline trùng chức năng.
