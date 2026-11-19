param(
    [Parameter(Mandatory)] [string]$OutputFile,
    [Parameter(Mandatory)] [string]$CompletionFile
)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $CompletionFile) { throw 'Use a fresh completion marker.' }
$stream = [IO.File]::Open($OutputFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
$writer = [IO.StreamWriter]::new($stream, [Text.UTF8Encoding]::new($false))
$writer.AutoFlush = $true
$counters = [ordered]@{
    cpu_percent = '\Processor(_Total)\% Processor Time'
    disk_read_bytes_s = '\PhysicalDisk(_Total)\Disk Read Bytes/sec'
    disk_write_bytes_s = '\PhysicalDisk(_Total)\Disk Write Bytes/sec'
    available_memory_MiB = '\Memory\Available MBytes'
    pages_input_s = '\Memory\Pages Input/sec'
}
try {
    while ($true) {
        $sample = Get-Counter -Counter @($counters.Values) -MaxSamples 1
        $row = [ordered]@{ utc = $sample.Timestamp.ToUniversalTime().ToString('o') }
        foreach ($name in $counters.Keys) {
            $matchesForCounter = @($sample.CounterSamples | Where-Object {
                $_.Path.EndsWith($counters[$name], [StringComparison]::OrdinalIgnoreCase)
            })
            if ($matchesForCounter.Count -ne 1) { throw "Missing or duplicate $name performance counter." }
            $row[$name] = [Math]::Round($matchesForCounter[0].CookedValue, 3)
        }
        $vm = Get-Process -Name vmmemWSL -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($vm) {
            $row['wsl_working_bytes'] = $vm.WorkingSet64
            $row['wsl_cpu_seconds'] = $vm.CPU
        }
        $writer.WriteLine(($row | ConvertTo-Json -Compress))
        if (Test-Path -LiteralPath $CompletionFile) { break }
        Start-Sleep -Seconds 15
    }
}
finally {
    $writer.Dispose()
}
