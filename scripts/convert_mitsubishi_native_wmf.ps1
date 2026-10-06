Add-Type -AssemblyName System.Drawing
$sourceDir = Join-Path (Get-Location) 'Tudien\CATALOG_PHU_KIEN_DOC_LAP\MITSUBISHI_D04_DU_LIEU_MOI\native'
foreach ($source in Get-ChildItem -LiteralPath $sourceDir -Filter 'MIT-D04-*.wmf') {
    $image = [System.Drawing.Image]::FromFile($source.FullName)
    try {
        $width = 1800
        $height = [Math]::Max(300, [int]($width * $image.Height / $image.Width))
        $bitmap = [System.Drawing.Bitmap]::new($width, $height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([System.Drawing.Color]::White)
            $graphics.DrawImage($image, 0, 0, $width, $height)
            $bitmap.Save((Join-Path $sourceDir ($source.BaseName + '.png')), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $graphics.Dispose()
            $bitmap.Dispose()
        }
    } finally {
        $image.Dispose()
    }
}
