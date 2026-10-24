$ErrorActionPreference = 'Stop'

# Run this script from the folder where you want AURORA_GOLD_MASTER.csv saved.
$indexUrl = 'https://mtf.trading/mcx/index.json'
$apiBase  = 'https://mtf.trading/api/v1/mcx'
$symbols  = @('GOLDM', 'GOLDGUINEA', 'GOLDPETAL', 'GOLDTEN')
$daysToTry = 60  # Try 60 available sessions to target at least 30 usable dates.
$outputPath = Join-Path (Get-Location) 'AURORA_GOLD_MASTER.csv'

Write-Host 'Reading available MCX dates...'
$index = Invoke-RestMethod -Uri $indexUrl -TimeoutSec 30
if (-not $index.dates -or $index.dates.Count -eq 0) {
    throw 'Date index did not contain a dates list. No output was created.'
}

$dates = @($index.dates | ForEach-Object { [string]$_.date } | Sort-Object -Descending)
$allRows = [System.Collections.Generic.List[object]]::new()
$successfulDates = [System.Collections.Generic.List[string]]::new()
$failedDates = [System.Collections.Generic.List[string]]::new()

for ($i = 0; $i -lt $dates.Count; $i++) {
    $dateCompact = $dates[$i]
    $dateIso = [datetime]::ParseExact($dateCompact, 'yyyyMMdd', [Globalization.CultureInfo]::InvariantCulture).ToString('yyyy-MM-dd')
    $uri = "$apiBase`?date=$dateIso&instr=FUTCOM&format=csv&limit=100000"
    Write-Progress -Activity 'Downloading MCX FUTCOM history' -Status "$dateIso ($($i + 1)/$($dates.Count))" -PercentComplete ((($i + 1) / $dates.Count) * 100)

    try {
        $response = Invoke-WebRequest -Uri $uri -TimeoutSec 45 -Headers @{ 'Accept' = 'text/csv,application/octet-stream,*/*' }
        $content = [string]$response.Content
        if ([string]::IsNullOrWhiteSpace($content)) { throw 'Empty response' }
        $rows = @($content | ConvertFrom-Csv)
        if ($rows.Count -eq 0) { throw 'Response did not parse as CSV rows' }

        # Handle the source's documented column names and tolerate harmless case differences.
        $first = $rows[0]
        $propertyNames = @($first.PSObject.Properties.Name)
        $symbolColumn = $propertyNames | Where-Object { $_ -ieq 'Symbol' } | Select-Object -First 1
        $instrumentColumn = $propertyNames | Where-Object { $_ -ieq 'InstrumentName' -or $_ -ieq 'Instrument Name' } | Select-Object -First 1
        if (-not $symbolColumn) { throw "CSV has no Symbol column. Columns: $($propertyNames -join ', ')" }

        $filtered = @($rows | Where-Object {
            $symbol = [string]($_.$symbolColumn)
            $symbol -and ($symbols -contains $symbol.Trim().ToUpperInvariant()) -and
            (-not $instrumentColumn -or ([string]($_.$instrumentColumn)).Trim().ToUpperInvariant() -eq 'FUTCOM')
        })

        if ($filtered.Count -gt 0) {
            foreach ($row in $filtered) { $allRows.Add($row) }
            $successfulDates.Add($dateIso)
            Write-Host "OK  $dateIso - $($filtered.Count) matching futures rows"
        } else {
            $failedDates.Add("$dateIso (no matching rows)")
            Write-Warning "$dateIso returned no rows for the four target symbols."
        }
    }
    catch {
        $failedDates.Add("$dateIso ($($_.Exception.Message))")
        Write-Warning "Skipped $dateIso : $($_.Exception.Message)"
    }
    Start-Sleep -Milliseconds 150
}
Write-Progress -Activity 'Downloading MCX FUTCOM history' -Completed

if ($allRows.Count -eq 0) {
    throw 'No matching rows were downloaded. Check endpoint availability; no output was created.'
}

# Deduplicate exact repeated rows without dropping distinct expiry contracts.
$finalRows = $allRows.ToArray()
$finalRows | Export-Csv -LiteralPath $outputPath -NoTypeInformation -Encoding UTF8

Write-Host ''
Write-Host "DONE: $outputPath" -ForegroundColor Green
Write-Host "Rows saved: $($finalRows.Count)"
Write-Host "Dates with matching data: $($successfulDates.Count)"
Write-Host "Dates skipped/empty: $($failedDates.Count)"
if ($successfulDates.Count -lt 30) {
    Write-Warning 'Fewer than 30 dates returned matching data. Increase $daysToTry and run again, or check source coverage.'
}
if ($failedDates.Count -gt 0) {
    Write-Host 'Skipped dates (first 15):'
    $failedDates | Select-Object -First 15 | ForEach-Object { Write-Host " - $_" }
}
