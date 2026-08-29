#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$InstallHostPackages,
    [switch]$IncludeGitHubCli,
    [switch]$InstallDockerDesktop,
    [switch]$BuildContainer,
    [switch]$RunContainerClearance,
    [switch]$OpenVsCode,
    [string]$ImageName = "sigil-quarto-actions:standalone",
    [string]$SigilbookPath = "..\sigilbook",
    [string]$WorkflowLayer = "examples",
    [string]$PythonPackage = "python314"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$DevcontainerDockerfile = Join-Path $RepoRoot ".devcontainer\Dockerfile"
$ValidChocolateyExitCodes = @(0, 1605, 1614, 1641, 3010)

function Invoke-CheckedNative {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [int[]]$ValidExitCodes = @(0)
    )

    Write-Host ">>> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    if ($ValidExitCodes -notcontains $exitCode) {
        throw "$FilePath exited with $exitCode"
    }
}

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-HostPackages {
    if (-not (Test-Command choco)) {
        throw "Chocolatey is not on PATH. Install Chocolatey first, then rerun with -InstallHostPackages."
    }

    $packages = @(
        "git",
        $PythonPackage,
        "vscode.install",
        "quarto",
        "pandoc"
    )
    if ($IncludeGitHubCli) {
        $packages += "gh"
    }
    if ($InstallDockerDesktop) {
        $packages += "docker-desktop"
    }

    Install-ChocolateyPackageList -Packages $packages
}

function Install-ChocolateyPackageList {
    param([Parameter(Mandatory = $true)][string[]]$Packages)

    if (-not (Test-Command choco)) {
        throw "Chocolatey is not on PATH. Install Chocolatey first."
    }

    Invoke-CheckedNative `
        -FilePath "choco" `
        -Arguments (@("upgrade") + $Packages + @("-y")) `
        -ValidExitCodes $ValidChocolateyExitCodes

    $profileModule = Join-Path $env:ChocolateyInstall "helpers\chocolateyProfile.psm1"
    if (Test-Path -LiteralPath $profileModule) {
        Import-Module $profileModule
        refreshenv
    }
}

function Assert-StandaloneInputs {
    if (-not (Test-Path -LiteralPath $DevcontainerDockerfile)) {
        throw "Missing .devcontainer/Dockerfile"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "clear-workflows\sigil_workflow_clear.py"))) {
        throw "Missing clear-workflows/sigil_workflow_clear.py"
    }
}

function Build-StandaloneContainer {
    if (-not (Test-Command docker)) {
        throw "Docker is not on PATH. Install/start Docker Desktop first."
    }
    Push-Location $RepoRoot
    try {
        Invoke-CheckedNative `
            -FilePath "docker" `
            -Arguments @("build", "-t", $ImageName, "-f", ".devcontainer/Dockerfile", ".")
    }
    finally {
        Pop-Location
    }
}

function Invoke-ContainerClearance {
    if (-not (Test-Command docker)) {
        throw "Docker is not on PATH. Install/start Docker Desktop first."
    }
    $resolvedSigilbook = (Resolve-Path -LiteralPath (Join-Path $RepoRoot $SigilbookPath)).Path
    $repoMount = "${RepoRoot}:/workspace/sigil-quarto-actions"
    $sigilbookMount = "${resolvedSigilbook}:/workspace/sigilbook:ro"

    Invoke-CheckedNative `
        -FilePath "docker" `
        -Arguments @(
            "run",
            "--rm",
            "-v",
            $repoMount,
            "-v",
            $sigilbookMount,
            "-w",
            "/workspace/sigil-quarto-actions",
            $ImageName,
            "python3",
            "clear-workflows/sigil_workflow_clear.py",
            "--sigilbook-path",
            "/workspace/sigilbook",
            "--resident-path",
            "/workspace/sigil-quarto-actions",
            "--workflow-layer",
            $WorkflowLayer,
            "--witness-output",
            "/workspace/sigil-quarto-actions/sigil-clearance-witness.container.json",
            "--fail-on-hold",
            "false"
        )
}

Assert-StandaloneInputs

if ($InstallHostPackages) {
    Install-HostPackages
}
elseif ($InstallDockerDesktop) {
    Install-ChocolateyPackageList -Packages @("docker-desktop")
}

if ($BuildContainer) {
    Build-StandaloneContainer
}

if ($RunContainerClearance) {
    Invoke-ContainerClearance
}

if ($OpenVsCode) {
    if (-not (Test-Command code)) {
        throw "VS Code CLI 'code' is not on PATH."
    }
    Push-Location $RepoRoot
    try {
        Invoke-CheckedNative -FilePath "code" -Arguments @(".")
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Sigil Quarto standalone path is ready."
if (-not (Test-Command docker)) {
    Write-Host "Docker CLI was not found. For the devcontainer/container path, run:"
    Write-Host "  .\setup\install-sigil-quarto-standalone-windows.ps1 -InstallDockerDesktop"
}
Write-Host "Fast commands:"
Write-Host "  code ."
Write-Host "  docker build -t $ImageName -f .devcontainer/Dockerfile ."
Write-Host "  python clear-workflows/sigil_workflow_clear.py --sigilbook-path ..\sigilbook --resident-path . --workflow-layer $WorkflowLayer --witness-output sigil-clearance-witness.local.json --fail-on-hold false"
Write-Host "  python play-knext-round/sigil_knext_round.py --sigilbook-path ..\sigilbook --resident-path . --clearance-witness sigil-clearance-witness.local.json --witness-output sigil-knext-round-witness.local.json --fail-on-hold false"
Write-Host "  python canonicalize-dokumenta/sigil_dokumenta_project.py --sigilbook-path ..\sigilbook --resident-path . --project-path . --clearance-witness sigil-clearance-witness.local.json --witness-output sigil-dokumenta-project-witness.local.json --fail-on-hold false"
