$files = Get-ChildItem -Path "e:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB" -Filter "thong_tin_thiet_bi.json" -Recurse -File
$errors = @()
$totalDevices = 0
$devicesWithPrice = 0
$devicesWithoutPrice = 0
$byBrand = @{}

foreach ($file in $files) {
    try {
        $content = [System.IO.File]::ReadAllText($file.FullName)
        $json = $content | ConvertFrom-Json -ErrorAction Stop

        # Extract brand from path
        $pathParts = $file.DirectoryName -split '\\'
        $brandIndex = [array]::IndexOf($pathParts, 'CatalogTB') + 1
        $brand = if ($brandIndex -lt $pathParts.Count) { $pathParts[$brandIndex] } else { "Unknown" }

        if (-not $byBrand.ContainsKey($brand)) {
            $byBrand[$brand] = @{Total=0; WithPrice=0; WithoutPrice=0}
        }

        $totalDevices++
        $byBrand[$brand].Total++

        # Check if price exists
        if ($json.gia -and $json.gia -ne "-" -and $json.gia -ne "" -and $json.gia -ne "N/A") {
            $devicesWithPrice++
            $byBrand[$brand].WithPrice++
        } else {
            $devicesWithoutPrice++
            $byBrand[$brand].WithoutPrice++
        }
    } catch {
        $errors += "$($file.FullName): $($_.Exception.Message)"
    }
}

Write-Output "VALIDATION_COMPLETE"
Write-Output "TOTAL_FILES:$($files.Count)"
Write-Output "TOTAL_DEVICES:$totalDevices"
Write-Output "WITH_PRICE:$devicesWithPrice"
Write-Output "WITHOUT_PRICE:$devicesWithoutPrice"
Write-Output "JSON_ERRORS:$($errors.Count)"

if ($errors.Count -gt 0) {
    Write-Output "ERRORS:"
    $errors | ForEach-Object { Write-Output $_ }
}

Write-Output "BY_BRAND:"
$byBrand.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Output "$($_.Key)|$($_.Value.Total)|$($_.Value.WithPrice)|$($_.Value.WithoutPrice)"
}
