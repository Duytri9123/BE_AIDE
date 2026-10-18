$files = Get-ChildItem -Path "e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB" -Filter "thong_tin_thiet_bi.json" -Recurse -File
$samplesWithoutPrice = @()
$count = 0

foreach ($file in $files) {
    if ($count -ge 50) { break }
    try {
        $content = [System.IO.File]::ReadAllText($file.FullName)
        $json = $content | ConvertFrom-Json -ErrorAction Stop

        # Extract brand from path
        $pathParts = $file.DirectoryName -split '\\'
        $brandIndex = [array]::IndexOf($pathParts, 'CatalogTB') + 1
        $brand = if ($brandIndex -lt $pathParts.Count) { $pathParts[$brandIndex] } else { "Unknown" }

        # Check if price is missing
        if (-not $json.gia -or $json.gia -eq "-" -or $json.gia -eq "" -or $json.gia -eq "N/A") {
            $samplesWithoutPrice += @{
                Brand = $brand
                ProductName = $json.ten_san_pham
                Code = if ($json.ma_dong_san_pham) { $json.ma_dong_san_pham } else { "N/A" }
                Path = $file.FullName -replace 'E:\\duytristool\\AIDE_website\\BE_AIDE\\data\\CatalogTB\\', ''
            }
            $count++
        }
    } catch {
        # Skip errors
    }
}

Write-Output "SAMPLES_WITHOUT_PRICE:"
$samplesWithoutPrice | ForEach-Object {
    Write-Output "$($_.Brand)|$($_.ProductName)|$($_.Code)|$($_.Path)"
}
