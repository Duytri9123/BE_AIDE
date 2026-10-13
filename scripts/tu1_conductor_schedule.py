"""Connection-based conductor proposals, kept separate from CAD identity."""
def build_schedule(branches):
 rows=[]
 def add(tag,origin,destination,kind,size,status):
  rows.append({'device':tag,'from':origin,'to':destination,'conductor':kind,'size':size,'status':status,'length_m':None,'length_status':'Chưa đo tuyến 3D/đi dây; không lấy khoảng cách thẳng CAD làm chiều dài đặt hàng'})
 add('QF0 đầu vào','Nguồn ngoài tủ','MCCB tổng 3P + thanh N','Cáp DSTA 4×95 mm² theo PDF; đầu cốt tương thích vật liệu ruột','4×95 mm²','PDF ghi DSTA; cần xác nhận ruột Cu/Al từ quy cách cáp thực tế và đầu cốt MCCB, không tự suy từ chữ DSTA')
 add('QF0 đầu ra','MCCB tổng','Hệ phân phối R/S/T','Thanh đồng cứng có bọc/che chắn hoặc thanh đồng mềm cách điện','Dự trù Cu 25×5 mm mỗi pha; phương án cáp Cu mềm 1×95 mm²/pha','Kích thước bố trí sơ bộ cho 200 A, chưa xác nhận ampacity, nhiệt độ, Icw/Ipk hay cỡ đầu nối; không coi 125 mm² đồng thanh tương đương 95 mm² cáp')
 for row in range(1,3):
  add(f'Dãy MCB {row}','Hệ phân phối R/S/T','Đầu vào MCB dãy '+str(row),'Đồng phân phối kiểu xương cá: trục cấp + các nhánh đồng; hoặc thanh lược hãng phù hợp','Chưa chốt tiết diện trục/nhánh; chịu bảo vệ phía trước 200 A hoặc thêm bảo vệ cấp hàng','Không dùng thanh lược 63/100 A sau MCCB 200 A nếu chưa kiểm tra tải và bảo vệ. Dãy 1 trộn 2P/3P: không dùng một thanh lược 3P xuyên suốt. Nhánh đồng phải hợp cọc đấu, bước cực và có che chắn; không vẽ giao nhau thành nối pha')
 for b in branches:
  add(b['id'],f"MCB {b['id']} đầu ra",b['load'],'Cáp nhánh theo PDF; dây Cu mềm cách điện cho đoạn nối nội bộ nếu phù hợp cọc đấu',b['cable_source'],
   'Giữ tiết diện nhánh theo PDF. Đoạn nội bộ chỉ đề xuất cùng tiết diện; kiểm tra cách lắp, nhiệt, bó dây và dòng cho phép. '+('30→32 A còn chờ kiểm tra bảo vệ cáp.' if b['source_current_A']==30 else ''))
 add('FU1–FU3','R/S/T phía nguồn đo lường','Dãy 3 đế cầu chì','Dây Cu mềm cách điện, đầu cốt/ferrule','Dự trù 1,5 mm²','Đoạn trước cầu chì phải xét bảo vệ phía nguồn và tuyến ngắn được bảo vệ cơ khí; không coi cầu chì 2 A bảo vệ đoạn nằm trước nó')
 add('HL_R','Sau FU1 + N','Đèn đỏ R','Dây Cu mềm cách điện 450/750 V','2 dây × 0,75–1 mm²','Đề xuất cho đèn 230 V pha–N; chọn tiết diện phù hợp cọc và cầu chì thực chọn')
 add('HL_Y','Sau FU2 + N','Đèn vàng Y','Dây Cu mềm cách điện 450/750 V','2 dây × 0,75–1 mm²','Đề xuất cho đèn 230 V pha–N; không nối 400 V vào cấu hình đèn 230 V')
 add('HL_B','Sau FU3 + N','Đèn xanh dương B','Dây Cu mềm cách điện 450/750 V','2 dây × 0,75–1 mm²','Đề xuất cho đèn 230 V pha–N; không coi màu dây là bằng chứng xác định pha')
 add('SA','Sau FU1/FU2/FU3 và N','Công tắc chọn vôn','Dây Cu mềm cách điện 450/750 V','Dự trù 1 mm² mỗi dây','Số dây/cọc theo sơ đồ tiếp điểm A007 và công tắc thực tế; không suy từ số vị trí mặt núm')
 add('PV','Hai cọc ra công tắc chọn vôn','Omega BE-96','Dây Cu mềm cách điện 450/750 V','2 dây × 1 mm²','Đề xuất mạch đo đã bảo vệ bằng cầu chì; không phải mạch CT 5 A')
 add('SHT trong QF0','Nguồn điều khiển đã bảo vệ + tiếp điểm báo cháy','Cuộn shunt trip MCCB','Dây Cu mềm cách điện; cáp tín hiệu riêng nếu giao diện yêu cầu','Dự trù 0,75–1 mm²; số lõi chưa chốt','Phải biết điện áp/cuộn SHT, dòng hút, chiều dài, logic báo cháy và phân cách mạch; không lấy dây tải 200 A cho SHT')
 add('N','Trung tính nguồn','Một thanh N → trung tính các nhánh','Dây/cáp trung tính hoặc đồng thanh gá cách điện','Nguồn N thuộc cáp 4×95; N nhánh 1,5/2,5/4/6 mm² theo bảng nhánh','Chưa chọn tiết diện thanh N và kiểm tra đủ đầu dây; dòng N cần xét mất cân bằng/hài, không giảm tiết diện chỉ vì tải 3 pha')
 add('PE','Tiếp địa nguồn + vỏ tủ','Một thanh PE → PE các nhánh','Dây Cu bảo vệ xanh-vàng; dây mềm liên kết cánh','PE nguồn dự trù Cu 50 mm² nếu dây pha Cu 95 mm²; PE nhánh theo PDF; nối cánh dự trù 4 mm²','PE nguồn chưa có trong PDF, giá trị là đề xuất theo giả định cùng vật liệu; cần kiểm tra nhiệt ngắn mạch/đường sự cố. Chưa chốt khả năng đấu của thanh PE CAD nhỏ')
 return rows
