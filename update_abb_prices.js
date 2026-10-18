const fs = require('fs');
const path = require('path');

const ABB_FILES = [
    "A2_1P", "A2_2P", "A2_3P", "A2_4P", "A3_3P", "A3_4P",
    "ABB_D03_C2_I08", "AX115_30_11_3P", "AX12_30_10_3P", "AX150_30_11_3P",
    "AX18_30_10_3P", "AX25_30_10_3P", "AX32_30_10_3P", "AX40_30_10_3P",
    "AX50_30_11_3P", "AX65_30_11_3P", "AX80_30_11_3P", "AX95_30_11_3P",
    "AX9_30_10_3P", "CAL5_11", "DS201L_1P+N", "FH202_2P", "FH204_4P",
    "OVR_T1_25_255", "OVR_T1_25_440_50", "OVR_T1_2L_25_255",
    "OVR_T1_2L_25_255_TS", "OVR_T1_3L_25_255", "OVR_T1_3L_25_255_TS",
    "OVR_T1_3N_25_255", "OVR_T1_3N_25_255_TS", "OVR_T1_4L_25_255",
    "OVR_T1_4L_25_255_TS", "S200_1P", "S200_2P", "S200_3P", "S200_4P",
    "S280UC_K_1P", "S280UC_K_2P", "S280UC_K_3P", "S280UC_K_4P",
    "SH200_1P", "SH200_2P", "SH200_3P", "SH200_4P",
    "T1_3P", "T1_4P", "T2_3P", "T2_4P", "T3_3P", "T3_4P",
    "T4_3P", "T4_4P", "T5_3P", "T5_4P", "T6_3P", "T6_4P",
    "T7M_3P", "T7M_4P", "T7_3P", "T7_4P",
    "TA25_DU", "TA42_DU", "TA75_DU", "TA80_DU",
    "VE5_1", "VE5_2",
    "XT1_3P", "XT1_4P", "XT2_3P", "XT2_4P",
    "XT3_3P", "XT3_4P", "XT4_3P", "XT4_4P"
];

const BASE_PATH = 'E:\\duytristool\\AIDE_website\\BE_AIDE\\data\\CatalogTB\\ABB\\ThietBi';

let successCount = 0;
let skipCount = 0;
let errorCount = 0;

console.log('='.repeat(70));
console.log('CẬP NHẬT GIÁ THIẾT BỊ ABB');
console.log('='.repeat(70));
console.log(`Tổng số file cần cập nhật: ${ABB_FILES.length}`);
console.log(`Ngày cập nhật: ${new Date().toISOString().split('T')[0]}`);
console.log('='.repeat(70));
console.log('');

ABB_FILES.forEach(folder => {
    const filePath = path.join(BASE_PATH, folder, 'thong_tin_thiet_bi.json');

    try {
        if (!fs.existsSync(filePath)) {
            console.log(`✗ ${folder}: File không tồn tại`);
            errorCount++;
            return;
        }

        const content = fs.readFileSync(filePath, 'utf8');
        const data = JSON.parse(content);

        // Check if gia_ban already exists
        if (data.gia_ban) {
            console.log(`⚠ ${folder}: Đã có gia_ban, bỏ qua`);
            skipCount++;
            return;
        }

        // Get product code
        const maSanPham = data.ma_dong_san_pham || 'N/A';

        // Add gia_ban field
        data.gia_ban = {
            don_gia: "-",
            don_vi_tien_te: "VND",
            trang_thai: "Chưa có giá",
            hang: "ABB",
            ma_san_pham: maSanPham,
            ghi_chu: "Chưa tìm được giá tin cậy từ nguồn chính thức ABB hoặc đại lý VN. Cần liên hệ đại lý để báo giá chính xác.",
            nguon_tham_khao: [
                "https://new.abb.com/low-voltage",
                "https://new.abb.com/products"
            ],
            ngay_cap_nhat: new Date().toISOString().split('T')[0],
            muc_do_tin_cay: "Tham khảo - cần xác nhận với nhà cung cấp"
        };

        // Write back to file
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');

        console.log(`✓ ${folder}: ${data.ten_san_pham}`);
        successCount++;

    } catch (error) {
        console.log(`✗ ${folder}: Lỗi - ${error.message}`);
        errorCount++;
    }
});

console.log('');
console.log('='.repeat(70));
console.log('KẾT QUẢ');
console.log('='.repeat(70));
console.log(`✓ Thành công: ${successCount}`);
console.log(`⚠ Bỏ qua: ${skipCount}`);
console.log(`✗ Lỗi: ${errorCount}`);
console.log(`Tổng: ${ABB_FILES.length}`);
console.log('='.repeat(70));
