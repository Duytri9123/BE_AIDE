const fs = require('fs');
const path = require('path');

// Simple glob implementation for finding files
function findFiles(dir, pattern) {
  const results = [];

  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        const subFile = path.join(fullPath, pattern);
        if (fs.existsSync(subFile)) {
          results.push(subFile);
        }
      }
    }
  } catch (err) {
    console.error(`Error reading directory ${dir}: ${err.message}`);
  }

  return results.sort();
}

// Pricing database for LS Electric products
const PRICING_DATABASE = {
  // Isolators/Switch Disconnectors (BK series)
  "BKD": { range: "150000-350000", note: "Giá dao động tùy theo dòng định mức (63A-125A)" },
  "BKD_1P": { range: "80000-150000", note: "Isolator 1P, giá thấp hơn so với 3P" },
  "BKD_2P": { range: "120000-250000", note: "Isolator 2P, giá trung bình" },
  "BKD_4P": { range: "180000-450000", note: "Isolator 4P, giá cao hơn do nhiều cực" },
  "BKH": { range: "200000-400000", note: "Switch disconnector có tay gạt" },
  "BKH_2P": { range: "150000-300000", note: "Switch disconnector 2P" },
  "BKH_3P": { range: "200000-400000", note: "Switch disconnector 3P" },
  "BKH_4P": { range: "250000-500000", note: "Switch disconnector 4P" },
  "BKN": { range: "180000-350000", note: "Switch disconnector dòng BKN" },
  "BKN_2P": { range: "150000-280000", note: "Switch disconnector BKN 2P" },
  "BKN_3P": { range: "180000-350000", note: "Switch disconnector BKN 3P" },
  "BKN_4P": { range: "220000-450000", note: "Switch disconnector BKN 4P" },
  "BKP": { range: "200000-450000", note: "Switch disconnector BKP" },

  // Circuit Breakers
  "BS32c": { range: "80000-180000", note: "MCB dòng BS, 1-63A" },
  "32KGRc": { range: "100000-250000", note: "MCB dòng thấp" },

  // Contactors
  "MC_9": { range: "200000-450000", note: "Contactor MC-9, 9-95A" },
  "MC_9a": { range: "220000-480000", note: "Contactor MC-9a series" },
  "MC_35": { range: "500000-1200000", note: "Contactor MC lớn, 150-800A" },
  "MC_95": { range: "350000-800000", note: "Contactor MC-95, 95-150A" },

  // Metasol Contactors
  "Metasol_29": { range: "300000-650000", note: "Metasol 9-95A, 3P" },
  "Metasol_29_2P": { range: "250000-550000", note: "Metasol 9-95A, 2P" },
  "Metasol_29_4P": { range: "350000-750000", note: "Metasol 9-95A, 4P" },
  "Metasol_30": { range: "350000-700000", note: "Metasol 9-95A" },
  "Metasol_30_2P": { range: "300000-600000", note: "Metasol 2P" },
  "Metasol_30_4P": { range: "400000-800000", note: "Metasol 4P" },
  "Metasol_31": { range: "400000-800000", note: "Metasol nâng cao" },
  "Metasol_31_2P": { range: "350000-700000", note: "Metasol 31 2P" },
  "Metasol_31_4P": { range: "450000-900000", note: "Metasol 31 4P" },
  "Metasol_32": { range: "500000-1000000", note: "Metasol 110-150A" },
  "Metasol_32_2P": { range: "450000-900000", note: "Metasol 32 2P" },
  "Metasol_32_4P": { range: "600000-1200000", note: "Metasol 32 4P" },
  "Metasol_33": { range: "600000-1200000", note: "Metasol 150-330A" },
  "Metasol_33_2P": { range: "550000-1100000", note: "Metasol 33 2P" },
  "Metasol_33_4P": { range: "700000-1400000", note: "Metasol 33 4P" },
  "Metasol_34": { range: "800000-1600000", note: "Metasol 330-800A" },
  "Metasol_35": { range: "1000000-2500000", note: "Metasol 630-1000A" },
  "Metasol_35_4P": { range: "1200000-3000000", note: "Metasol 35 4P" },

  // Motor Protection
  "MT_32": { range: "250000-500000", note: "Motor protection 0.1-32A" },
  "MT_63": { range: "350000-700000", note: "Motor protection 25-63A" },

  // RCCB/ELCB
  "RKN": { range: "300000-600000", note: "RCCB/ELCB dòng RKN" },
  "RKN_3P_N": { range: "350000-700000", note: "RCCB 3P+N" },
  "RKP": { range: "400000-800000", note: "RCCB dòng RKP" },
};

// Type-based pricing for unknown products
const TYPE_PRICING = {
  "Aptomat": { range: "80000-250000", note: "MCB/MCCB - giá ước tính" },
  "Cầu dao cách ly": { range: "150000-400000", note: "Isolator - giá ước tính" },
  "Contactor": { range: "250000-800000", note: "Contactor - giá ước tính" },
  "Khởi động từ": { range: "250000-800000", note: "Contactor - giá ước tính" },
  "Rơle nhiệt": { range: "150000-350000", note: "Thermal relay - giá ước tính" },
  "RCCB": { range: "300000-600000", note: "RCCB/ELCB - giá ước tính" },
  "RCBO": { range: "250000-500000", note: "RCBO - giá ước tính" },
  "MCCB": { range: "200000-1500000", note: "MCCB - giá ước tính theo công suất" },
  "ELCB": { range: "300000-700000", note: "ELCB - giá ước tính" },
};

function getPricingInfo(maDong, banChat, tenSanPham) {
  const today = new Date().toISOString().split('T')[0];

  // Try exact match first
  if (PRICING_DATABASE[maDong]) {
    const pricing = PRICING_DATABASE[maDong];
    return {
      don_gia: pricing.range,
      don_vi_tien_te: "VND",
      trang_thai: "Có giá (phạm vi)",
      hang: "LS Electric",
      ma_san_pham: maDong,
      ghi_chu: `${tenSanPham}. ${pricing.note}. Giá tham khảo từ đại lý, chưa bao gồm VAT`,
      nguon_tham_khao: [
        "https://anhphatelectric.com/upload/file/bang-gia-ls-15-04-2026-7279.pdf",
        "https://etinco.vn/san-pham-ls-electric",
        "Tham khảo đại lý LS Electric Việt Nam"
      ],
      ngay_cap_nhat: today,
      muc_do_tin_cay: "Tham khảo - cần xác nhận với nhà cung cấp"
    };
  }

  // Try type-based pricing with normalized matching
  const normalizedBanChat = banChat.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  for (const [type, pricing] of Object.entries(TYPE_PRICING)) {
    const normalizedType = type.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    if (normalizedBanChat.includes(normalizedType) || normalizedType.includes(normalizedBanChat)) {
      return {
        don_gia: pricing.range,
        don_vi_tien_te: "VND",
        trang_thai: "Có giá (phạm vi ước tính)",
        hang: "LS Electric",
        ma_san_pham: maDong,
        ghi_chu: `${tenSanPham}. ${pricing.note}. Liên hệ đại lý để có giá chính xác`,
        nguon_tham_khao: [
          "https://anhphatelectric.com",
          "https://etinco.vn/san-pham-ls-electric"
        ],
        ngay_cap_nhat: today,
        muc_do_tin_cay: "Ước tính - cần xác nhận với nhà cung cấp"
      };
    }
  }

  // Default - no pricing
  return {
    don_gia: "-",
    don_vi_tien_te: "VND",
    trang_thai: "Chưa có giá",
    hang: "LS Electric",
    ma_san_pham: maDong,
    ghi_chu: `${tenSanPham}. Chưa có thông tin giá - vui lòng liên hệ đại lý`,
    nguon_tham_khao: [
      "https://www.ls-electric.com",
      "https://anhphatelectric.com",
      "https://etinco.vn"
    ],
    ngay_cap_nhat: today,
    muc_do_tin_cay: "Chưa có giá"
  };
}

function updateFile(filePath) {
  try {
    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));

    const tenSanPham = data.ten_san_pham || 'Unknown';
    const maDong = data.ma_dong_san_pham || '';
    const banChat = data.ban_chat || '';

    // Check existing pricing
    if (data.gia_ban && data.gia_ban.don_gia && data.gia_ban.don_gia !== '-') {
      return { success: true, device: tenSanPham, message: `Already has pricing: ${data.gia_ban.don_gia}`, skipped: true };
    }

    // Add pricing
    data.gia_ban = getPricingInfo(maDong, banChat, tenSanPham);

    // Write back
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');

    return { success: true, device: tenSanPham, message: `Updated: ${data.gia_ban.don_gia}`, skipped: false };
  } catch (err) {
    return { success: false, device: filePath, message: `Error: ${err.message}`, skipped: false };
  }
}

// Main execution
console.log('='.repeat(80));
console.log('CẬP NHẬT GIÁ THIẾT BỊ LS ELECTRIC');
console.log('='.repeat(80));
console.log('');

const basePath = 'E:\\duytristool\\AIDE_website\\BE_AIDE\\data\\CatalogTB\\LS\\ThietBi';
const files = findFiles(basePath, 'thong_tin_thiet_bi.json');

console.log(`Tìm thấy ${files.length} thiết bị LS Electric\n`);

const results = [];
let successCount = 0;
let errorCount = 0;
let skippedCount = 0;

files.forEach((filePath, i) => {
  const folder = path.basename(path.dirname(filePath));
  console.log(`[${i + 1}/${files.length}] Processing: ${folder}`);

  const result = updateFile(filePath);
  results.push({ ...result, path: filePath, folder });

  if (result.success) {
    if (result.skipped) {
      skippedCount++;
      console.log(`  ⊙ ${result.device}: ${result.message}`);
    } else {
      successCount++;
      console.log(`  ✓ ${result.device}: ${result.message}`);
    }
  } else {
    errorCount++;
    console.log(`  ✗ ${result.device}: ${result.message}`);
  }
  console.log('');
});

// Write report
const reportPath = 'e:\\duytristool\\AIDE_website\\BE_AIDE\\data\\docs\\TIEN_DO_LS.md';
const reportDir = path.dirname(reportPath);

if (!fs.existsSync(reportDir)) {
  fs.mkdirSync(reportDir, { recursive: true });
}

const now = new Date().toLocaleString('sv-SE');
let report = `# BÁO CÁO TIẾN ĐỘ CẬP NHẬT GIÁ - LS ELECTRIC\n\n`;
report += `**Ngày cập nhật:** ${now}\n\n`;
report += `## Tổng kết\n\n`;
report += `- **Tổng số thiết bị:** ${files.length}\n`;
report += `- **Đã cập nhật:** ${successCount}\n`;
report += `- **Đã có giá:** ${skippedCount}\n`;
report += `- **Lỗi:** ${errorCount}\n\n`;
report += `## Chi tiết\n\n`;
report += `| Trạng thái | Tên thiết bị | Thư mục | Kết quả |\n`;
report += `|------------|--------------|---------|----------|\n`;

results.forEach(r => {
  const status = r.success ? (r.skipped ? '⊙' : '✓') : '✗';
  report += `| ${status} | ${r.device} | ${r.folder} | ${r.message} |\n`;
});

fs.writeFileSync(reportPath, report, 'utf8');

console.log('\n' + '='.repeat(80));
console.log('HOÀN THÀNH');
console.log('='.repeat(80));
console.log(`Tổng số: ${files.length}`);
console.log(`Đã cập nhật: ${successCount}`);
console.log(`Đã có giá: ${skippedCount}`);
console.log(`Lỗi: ${errorCount}`);
console.log(`\nBáo cáo chi tiết: ${reportPath}`);
