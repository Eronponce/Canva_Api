param(
    [ValidateSet("start", "stop", "restart", "status", "open")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $ProjectRoot "logs"
$StdoutLog = Join-Path $LogsDir "server.stdout.log"
$StderrLog = Join-Path $LogsDir "server.stderr.log"
$PidFile = Join-Path $LogsDir "server.pid"
$Url = "http://127.0.0.1:5000"
$CondaPython = Join-Path $env:USERPROFILE ".conda\envs\canvas-bulk-panel\python.exe"

if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

function Get-PythonPath {
    if (Test-Path $CondaPython) {
        return $CondaPython
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    throw "Nao encontrei um python executavel. Instale o ambiente ou ajuste o PATH."
}

function Get-AppProcesses {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -like "*app.py*"
        }
}

function Test-AppRunning {
    param(
        [int]$ProcessId
    )

    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return [bool]$process
    } catch {
        return $false
    }
}

function Save-Pid {
    param(
        [int]$ProcessId
    )

    Set-Content -Path $PidFile -Value $ProcessId -Encoding ascii
}

function Remove-PidFile {
    if (Test-Path $PidFile) {
        Remove-Item -LiteralPath $PidFile -Force
    }
}

function Get-SavedPid {
    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $raw = (Get-Content -Path $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($raw -match "^\d+$") {
        return [int]$raw
    }

    return $null
}

function Start-App {
    $existing = Get-AppProcesses
    if ($existing) {
        $runningPid = $existing[0].ProcessId
        Save-Pid -ProcessId $runningPid
        Write-Host "Painel ja esta em execucao no PID $runningPid"
        Open-PanelUrl
        return
    }

    $pythonExe = Get-PythonPath
    $process = Start-Process `
        -FilePath $pythonExe `
        -ArgumentList "app.py" `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -PassThru

    Start-Sleep -Seconds 3
    Save-Pid -ProcessId $process.Id

    try {
        $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 10
        Write-Host "Painel iniciado com sucesso."
        Write-Host "URL: $Url"
        Write-Host "PID: $($process.Id)"
        Write-Host "HTTP: $($response.StatusCode)"
        Open-PanelUrl
    } catch {
        Write-Host "O processo foi iniciado, mas a URL ainda nao respondeu."
        Write-Host "PID: $($process.Id)"
        Write-Host "Verifique os logs em $StdoutLog e $StderrLog"
    }
}

function Stop-App {
    $stoppedAny = $false
    $savedPid = Get-SavedPid

    if ($savedPid -and (Test-AppRunning -ProcessId $savedPid)) {
        Stop-Process -Id $savedPid -Force
        Write-Host "Painel encerrado. PID: $savedPid"
        $stoppedAny = $true
    }

    $otherProcesses = Get-AppProcesses
    foreach ($process in $otherProcesses) {
        if (-not $savedPid -or $process.ProcessId -ne $savedPid) {
            Stop-Process -Id $process.ProcessId -Force
            Write-Host "Processo encerrado. PID: $($process.ProcessId)"
            $stoppedAny = $true
        }
    }

    Remove-PidFile

    if (-not $stoppedAny) {
        Write-Host "Nenhum processo do painel estava em execucao."
    }
}

function Show-Status {
    $processes = Get-AppProcesses
    if (-not $processes) {
        Write-Host "Painel parado."
        return
    }

    foreach ($process in $processes) {
        Write-Host "Painel em execucao."
        Write-Host "PID: $($process.ProcessId)"
        Write-Host "URL: $Url"
    }
}

function Open-PanelUrl {
    try {
        Start-Process $Url | Out-Null
    } catch {
        Write-Host "Nao foi possivel abrir o navegador automaticamente."
        Write-Host "Abra manualmente: $Url"
    }
}

switch ($Action) {
    "start" { Start-App }
    "stop" { Stop-App }
    "restart" {
        Stop-App
        Start-App
    }
    "status" { Show-Status }
    "open" { Open-PanelUrl }
}
