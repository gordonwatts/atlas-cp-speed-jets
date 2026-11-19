param(
    [ValidateRange(1, 999)] [int]$MonitorNumber = 1,
    [string]$Specification = 'contracts/final-shipment.json',
    [string]$QualificationOutput = 'results/validation/shipment-final-001',
    [string]$ProductionJournal,
    [ValidateSet('small', 'large', 'combined')] [string]$RecheckScope,
    [ValidateSet('nominal', 'full')] [string]$RecheckMode,
    [ValidateSet('AB', 'AC')] [string]$RecheckPair,
    [ValidateRange(1, 999)] [int]$RecheckNumber = 1
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$guestRoot = '/home/gwatts/atlas-cp-speed/jets-skill-c8a2374-20261117'
$recheckArguments = @($RecheckScope, $RecheckMode, $RecheckPair | Where-Object { $_ })
if ($recheckArguments.Count -notin @(0, 3)) {
    throw 'Supply scope, workload and pair together for a bounded recheck.'
}
$name = 'production'
$options = @()
if ($ProductionJournal) { $options = @('--production-output', $ProductionJournal) }
if ($recheckArguments.Count -eq 3) {
    $name = 'recheck-{0}-{1}-{2}-{3:d3}' -f $RecheckPair, $RecheckScope, $RecheckMode, $RecheckNumber
    $originalJournal = if ($ProductionJournal) { $ProductionJournal } else { "$QualificationOutput/production" }
    $options = @('--recheck-of', $originalJournal, '--recheck-scope', $RecheckScope,
                 '--recheck-mode', $RecheckMode, '--recheck-pair', $RecheckPair,
                 '--recheck-output', "$QualificationOutput/$name")
}
$suffix = 'monitor-{0:d3}' -f $MonitorNumber
$trace = "results/diagnostics/$name-$suffix"
$group = [IO.Directory]::CreateDirectory((Join-Path $PSScriptRoot $name))
$folder = (New-Item -ItemType Directory -Path (Join-Path $group.FullName $suffix)).FullName
$log = Join-Path $folder 'host.jsonl'
$done = Join-Path $folder 'host-completed.json'
$watch = Join-Path $PSScriptRoot 'watch-host.ps1'
$monitorArgs = @('-NoProfile', '-NonInteractive', '-File', ('"{0}"' -f $watch),
                 '-OutputFile', ('"{0}"' -f $log), '-CompletionFile', ('"{0}"' -f $done))
$started = [DateTimeOffset]::UtcNow
$returnCode = $null
$monitor = $null
try {
    $monitor = Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $monitorArgs -WindowStyle Hidden -PassThru -RedirectStandardError (Join-Path $folder 'monitor.err')
    for ($i = 0; $i -lt 40 -and -not $monitor.HasExited; $i++) {
        if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt 0) { break }
        Start-Sleep -Milliseconds 250
    }
    if ($monitor.HasExited -or -not (Test-Path -LiteralPath $log) -or (Get-Item -LiteralPath $log).Length -eq 0) {
        throw "Windows counter sampling failed to start in $folder."
    }
    & wsl.exe -d atlas_al9 --cd $guestRoot --exec bash tools/run_production_with_monitor.sh $Specification $trace @options
    $returnCode = $LASTEXITCODE
}
finally {
    $receipt = @{started_utc = $started.ToString('o'); ended_utc = [DateTimeOffset]::UtcNow.ToString('o')
                 wsl_exit = $returnCode; guest_trace = $trace; specification = $Specification; options = $options}
    [IO.File]::WriteAllText($done, ($receipt | ConvertTo-Json))
    if ($monitor -and -not $monitor.WaitForExit(25000)) { Write-Warning 'Windows counter sampler is still draining.' }
}
exit $returnCode
