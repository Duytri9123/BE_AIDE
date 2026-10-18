# Script to update Schneider Electric equipment prices
# This script adds pricing information to equipment JSON files

$scriptStartTime = Get-Date
$rootPath = "e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\Schneider"
$docsPath = "e:\duytristool\AIDE_website\BE_AIDE\docs"
$progressFile = "$docsPath\TIEN_DO_SCHNEIDER.md"

# Initialize counters
$totalFiles = 0
$updatedFiles = 0
$skippedFiles = 0
$errorFiles = @()

Write-Host "=== Starting Schneider Electric price update ===" -ForegroundColor Cyan

# Get all JSON files
$jsonFiles = Get-ChildItem -Path $rootPath -Recurse -Filter "thong_tin_thiet_bi.json"
$totalFiles = $jsonFiles.Count

Write-Host "Total files to process: $totalFiles" -ForegroundColor Green

# Price mapping based on product research
$priceRanges = @{
    "iC60" = @{
        "don_gia" = "150,000 - 500,000"
        "ghi_chu" = "Gia thay doi theo dong dinh muc (6A-63A) va duong cong (B,C,D)"
        "trang_thai" = "Co gia (pham vi)"
    }
    "C120" = @{
        "don_gia" = "200,000 - 600,000"
        "ghi_chu" = "MCB cong nghiep, gia theo dong dinh muc va so cuc"
        "trang_thai" = "Co gia (pham vi)"
    }
    "iK60N" = @{
        "don_gia" = "100,000 - 400,000"
        "ghi_chu" = "MCB pho thong, gia theo dong dinh muc"
        "trang_thai" = "Co gia (pham vi)"
    }
    "iCT" = @{
        "don_gia" = "80,000 - 300,000"
        "ghi_chu" = "MCB loai co ban"
        "trang_thai" = "Co gia (pham vi)"
    }
    "NS100" = @{
        "don_gia" = "1,500,000 - 4,000,000"
        "ghi_chu" = "MCCB Compact NS 100A, gia theo Trip unit va phu kien"
        "trang_thai" = "Co gia (pham vi)"
    }
    "NS400" = @{
        "don_gia" = "4,000,000 - 12,000,000"
        "ghi_chu" = "MCCB Compact NS 400A, gia theo Trip unit"
        "trang_thai" = "Co gia (pham vi)"
    }
    "NS630" = @{
        "don_gia" = "8,000,000 - 20,000,000"
        "ghi_chu" = "MCCB Compact NS 630A, gia theo cau hinh"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZC100" = @{
        "don_gia" = "800,000 - 2,500,000"
        "ghi_chu" = "MCCB EasyPact CVS 100A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZC250" = @{
        "don_gia" = "2,000,000 - 5,000,000"
        "ghi_chu" = "MCCB EasyPact CVS 250A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZC400" = @{
        "don_gia" = "3,500,000 - 8,000,000"
        "ghi_chu" = "MCCB EasyPact CVS 400A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZS100" = @{
        "don_gia" = "600,000 - 2,000,000"
        "ghi_chu" = "MCCB EasyPact EZS 100A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZS250" = @{
        "don_gia" = "1,800,000 - 4,500,000"
        "ghi_chu" = "MCCB EasyPact EZS 250A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZS400" = @{
        "don_gia" = "3,000,000 - 7,000,000"
        "ghi_chu" = "MCCB EasyPact EZS 400A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "EZCV250" = @{
        "don_gia" = "2,500,000 - 6,000,000"
        "ghi_chu" = "MCCB EasyPact CVS 250A with electronic"
        "trang_thai" = "Co gia (pham vi)"
    }
    "CVS100" = @{
        "don_gia" = "1,200,000 - 3,500,000"
        "ghi_chu" = "MCCB ComPacT CVS 100A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "CVS400" = @{
        "don_gia" = "4,500,000 - 11,000,000"
        "ghi_chu" = "MCCB ComPacT CVS 400A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "A9D" = @{
        "don_gia" = "400,000 - 1,200,000"
        "ghi_chu" = "RCCB/RCBO iDPN, gia theo so cuc va do nhay"
        "trang_thai" = "Co gia (pham vi)"
    }
    "iIDK" = @{
        "don_gia" = "300,000 - 900,000"
        "ghi_chu" = "RCCB dong iID, gia theo dong dinh muc"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1D9" = @{
        "don_gia" = "250,000 - 450,000"
        "ghi_chu" = "Contactor TeSys D 9-18A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1D25" = @{
        "don_gia" = "350,000 - 650,000"
        "ghi_chu" = "Contactor TeSys D 25-38A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1D40" = @{
        "don_gia" = "500,000 - 900,000"
        "ghi_chu" = "Contactor TeSys D 40-65A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1E06" = @{
        "don_gia" = "800,000 - 1,500,000"
        "ghi_chu" = "Contactor TeSys E 06-32A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1E25" = @{
        "don_gia" = "900,000 - 1,600,000"
        "ghi_chu" = "Contactor TeSys E 25-32A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1E32" = @{
        "don_gia" = "1,000,000 - 1,700,000"
        "ghi_chu" = "Contactor TeSys E 32A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1E160" = @{
        "don_gia" = "3,500,000 - 6,000,000"
        "ghi_chu" = "Contactor TeSys E 160A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1F115" = @{
        "don_gia" = "2,000,000 - 3,800,000"
        "ghi_chu" = "Contactor TeSys F 115A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1F150" = @{
        "don_gia" = "2,500,000 - 4,500,000"
        "ghi_chu" = "Contactor TeSys F 150A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1F185" = @{
        "don_gia" = "3,000,000 - 5,500,000"
        "ghi_chu" = "Contactor TeSys F 185A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1F225" = @{
        "don_gia" = "3,500,000 - 6,500,000"
        "ghi_chu" = "Contactor TeSys F 225A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1F265" = @{
        "don_gia" = "4,000,000 - 7,500,000"
        "ghi_chu" = "Contactor TeSys F 265A"
        "trang_thai" = "Co gia (pham vi)"
    }
    "LC1F330" = @{
        "don_gia" = "5,000,000 - 9,000,000"
        "ghi_chu" = "Contactor TeSys F 330A"
        "trang_thai" = "Co gia (pham vi)"
    }
}

# Reference sources
$nguonThamKhao = @(
    "https://schneider.net.vn"
    "https://www.se.com/vn/vi/"
    "https://etinco.vn"
    "https://dienquang.com"
)

# Process each file
$counter = 0
foreach ($file in $jsonFiles) {
    $counter++
    $percentComplete = [math]::Round(($counter / $totalFiles) * 100, 2)
    Write-Progress -Activity "Updating Schneider prices" -Status "File $counter/$totalFiles" -PercentComplete $percentComplete

    try {
        # Read JSON file
        $jsonContent = Get-Content $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json

        # Extract product code
        $productCode = $jsonContent.ma_dong_san_pham

        if (-not $productCode) {
            Write-Host "  [SKIP] $($file.Directory.Name): No product code" -ForegroundColor Yellow
            $skippedFiles++
            continue
        }

        # Check if price already exists
        if ($jsonContent.PSObject.Properties.Name -contains "gia_ban") {
            Write-Host "  [SKIP] $($file.Directory.Name): Already has price" -ForegroundColor Gray
            $skippedFiles++
            continue
        }

        # Find matching price range
        $priceInfo = $null
        foreach ($key in $priceRanges.Keys) {
            if ($productCode -like "*$key*") {
                $priceInfo = $priceRanges[$key]
                break
            }
        }

        # If no specific match, use default
        if (-not $priceInfo) {
            $priceInfo = @{
                "don_gia" = "-"
                "ghi_chu" = "Can xac dinh ma san pham cu the"
                "trang_thai" = "Chua co gia"
            }
        }

        # Create price object
        $giaBan = [PSCustomObject]@{
            don_gia = $priceInfo.don_gia
            don_vi_tien_te = "VND"
            trang_thai = $priceInfo.trang_thai
            hang = "Schneider Electric"
            ma_san_pham = $productCode
            ghi_chu = $priceInfo.ghi_chu
            nguon_tham_khao = $nguonThamKhao
            ngay_cap_nhat = (Get-Date -Format "yyyy-MM-dd")
            muc_do_tin_cay = "Tham khao - can xac nhan voi nha cung cap"
        }

        # Add to JSON object
        $jsonContent | Add-Member -MemberType NoteProperty -Name "gia_ban" -Value $giaBan -Force

        # Convert back to JSON with proper formatting
        $jsonOutput = $jsonContent | ConvertTo-Json -Depth 10 -Compress:$false

        # Write back to file with UTF8 encoding
        $jsonOutput | Out-File -FilePath $file.FullName -Encoding UTF8 -Force

        Write-Host "  [OK] $($file.Directory.Name): $productCode - $($priceInfo.don_gia)" -ForegroundColor Green
        $updatedFiles++

    } catch {
        Write-Host "  [ERROR] $($file.Directory.Name): $($_.Exception.Message)" -ForegroundColor Red
        $errorFiles += $file.FullName
    }
}

$scriptEndTime = Get-Date
$duration = $scriptEndTime - $scriptStartTime

Write-Host "`n=== COMPLETED ===" -ForegroundColor Cyan
Write-Host "Total files: $totalFiles" -ForegroundColor White
Write-Host "Updated: $updatedFiles" -ForegroundColor Green
Write-Host "Skipped: $skippedFiles" -ForegroundColor Yellow
Write-Host "Errors: $($errorFiles.Count)" -ForegroundColor Red
Write-Host "Duration: $($duration.ToString())" -ForegroundColor Cyan

# Create progress report
$report = "# Bao cao tien do cap nhat gia Schneider Electric`n`n"
$report += "**Thoi gian:** $scriptStartTime - $scriptEndTime`n"
$report += "**Thoi luong:** $($duration.ToString())`n`n"
$report += "## Thong ke`n`n"
$report += "- Tong so file: $totalFiles`n"
$report += "- Da cap nhat: $updatedFiles`n"
$report += "- Bo qua: $skippedFiles`n"
$report += "- Loi: $($errorFiles.Count)`n`n"

$report | Out-File -FilePath $progressFile -Encoding UTF8
Write-Host "`nProgress report: $progressFile" -ForegroundColor Cyan
