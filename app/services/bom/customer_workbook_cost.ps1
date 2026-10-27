param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference = 'Stop'
$request = Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$excel = $null
$book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3
    $book = $excel.Workbooks.Open([string]$request.workbook_path, 0, $true)
    $vt = $book.Worksheets.Item('VT')
    if ($null -ne $request.enclosure) {
        foreach ($entry in @{H9='thickness_mm';H10='height_mm';H11='width_mm';H12='depth_mm'}.GetEnumerator()) {
            $vt.Range($entry.Key).Value2 = [double]$request.enclosure.($entry.Value)
        }
        foreach ($entry in @{M9='location';M10='construction';M11='compartments';M12='side_panels';M13='compartmented';M14='door_layers';M15='accessories';M16='plinth_height_mm';D9='price_per_kg'}.GetEnumerator()) {
            $value = $request.enclosure.($entry.Value)
            if ($null -ne $value) {
                if ($value -is [ValueType]) { $value = [double]$value }
                $vt.Range($entry.Key).Value2 = $value
            }
        }
    }
    $bus = $book.Worksheets.Item('Busbar')
    $bus.Range('M6:P45').ClearContents()
    if ($null -ne $request.copper_price_per_kg) { $bus.Range('S2').Value2 = [double]$request.copper_price_per_kg }
    $index = 6
    foreach ($segment in $request.busbar_segments) {
        $bus.Range("M$index").Value2 = [double]$segment.width_mm
        $bus.Range("N$index").Value2 = [double]$segment.thickness_mm
        $bus.Range("O$index").Value2 = [double]$segment.length_mm
        $bus.Range("P$index").Value2 = [double]$segment.quantity
        $index++
    }
    $excel.CalculateFullRebuild()
    $busCalculation = $book.Worksheets.Item(('T' + [char]237 + 'nh Busbar'))
    $result = @{
        enclosure = @{ mass_kg=$vt.Range('H21').Value2; unit_price=$vt.Range('L21').Value2; price_per_kg=$vt.Range('D9').Value2 }
        busbar = @{ mass_kg=$busCalculation.Evaluate('SUM(I6:I45)'); unit_price=$bus.Range('T46').Value2; price_per_kg=$bus.Range('S2').Value2 }
    }
    $result | ConvertTo-Json -Depth 5 -Compress
} finally {
    if ($null -ne $book) { $book.Close($false) }
    if ($null -ne $excel) { $excel.Quit() }
    if ($null -ne $book) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($book) }
    if ($null -ne $excel) { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($excel) }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
