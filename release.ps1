param(
    [string]$Tag = "v1.0.0",
    [string]$Title = "",
    [string]$NotesFile = "CHANGELOG.md",
    [switch]$SkipAuth,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Resolve-GhCli {
    $candidates = @(
        (Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"),
        "gh"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -eq "gh") {
            $cmd = Get-Command gh -ErrorAction SilentlyContinue
            if ($cmd) {
                return $cmd.Source
            }
            continue
        }

        if (Test-Path $candidate) {
            return $candidate
        }
    }

    throw "GitHub CLI nao encontrada. Instale com: winget install --id GitHub.cli -e"
}

function Invoke-Step {
    param(
        [string]$Label,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host "==> $Label" -ForegroundColor Cyan
    & $Action
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

if (-not $Title) {
    $Title = $Tag
}

$ghPath = Resolve-GhCli

Invoke-Step "Repositorio" {
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($branch -ne "main") {
        throw "Execute o release a partir da branch main. Branch atual: $branch"
    }

    $status = git status --short
    if ($status) {
        throw "A worktree nao esta limpa. Faça commit/stash antes de criar o release."
    }

    Write-Host "Branch main confirmada e worktree limpa."
}

Invoke-Step "Tag" {
    $tagRef = git rev-parse -q --verify "refs/tags/$Tag" 2>$null
    if (-not $tagRef) {
        throw "Tag '$Tag' nao encontrada. Crie e publique a tag antes de gerar o release."
    }

    Write-Host "Tag encontrada: $Tag"
}

Invoke-Step "Arquivo de notas" {
    if (-not (Test-Path $NotesFile)) {
        throw "Arquivo de notas nao encontrado: $NotesFile"
    }

    Write-Host "Usando notas em: $NotesFile"
}

if (-not $SkipAuth) {
    Invoke-Step "Autenticacao GitHub" {
        & $ghPath auth status *> $null
        if ($LASTEXITCODE -ne 0) {
            if ($DryRun) {
                Write-Host "Dry run: autenticacao seria solicitada agora."
                return
            }

            Write-Host "Abrindo autenticacao do GitHub CLI..." -ForegroundColor Yellow
            & $ghPath auth login
        }

        Write-Host "GitHub CLI autenticado."
    }
}

Invoke-Step "Release no GitHub" {
    & $ghPath release view $Tag *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Ja existe um release para $Tag. Nada a fazer." -ForegroundColor Yellow
        return
    }

    if ($DryRun) {
        Write-Host "Dry run: seria executado:"
        Write-Host """$ghPath"" release create $Tag --title ""$Title"" --notes-file ""$NotesFile"""
        return
    }

    & $ghPath release create $Tag --title $Title --notes-file $NotesFile
    Write-Host "Release criado com sucesso para $Tag." -ForegroundColor Green
}
