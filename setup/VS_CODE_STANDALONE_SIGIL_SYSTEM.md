# VS Code Standalone Sigil System

This is the fast local Windows path for making `sigil-quarto-actions` a
standalone thin Sigil subsystem while keeping repository authority outside the
container. It uses Chocolatey for host packages and Docker/VS Code Dev
Containers for the isolated runtime.

## Host Bootstrap

Open an elevated PowerShell when installing host packages:

```powershell
.\setup\install-sigil-quarto-standalone-windows.ps1 -InstallHostPackages
```

The bootstrap uses these Chocolatey package IDs:

```powershell
choco upgrade git python314 vscode.install quarto pandoc -y
```

`gh` is optional because the Sigil KLI/QLI layer and Codex GitHub connector own
repository IO. Install it only when you want the virtual CLI projection locally:

```powershell
.\setup\install-sigil-quarto-standalone-windows.ps1 -InstallHostPackages -IncludeGitHubCli
```

Docker Desktop is only needed for the devcontainer/container path:

```powershell
.\setup\install-sigil-quarto-standalone-windows.ps1 -InstallDockerDesktop
```

## VS Code Loop

From this repository:

```powershell
code .
```

Use **Dev Containers: Reopen in Container**. The devcontainer mounts:

- this repository at `/workspace/sigil-quarto-actions`;
- sibling `../sigilbook` at `/workspace/sigilbook` read-only.

After the container is created, it runs the clearance checker once and writes
the witness to `/tmp/sigil-quarto-actions-clearance.json`.

## Container Commands

Build the standalone image:

```powershell
.\setup\install-sigil-quarto-standalone-windows.ps1 -BuildContainer
```

Run the clearance check inside the container:

```powershell
.\setup\install-sigil-quarto-standalone-windows.ps1 -RunContainerClearance
```

Or use the VS Code tasks:

- `Sigil: clear workflows locally`
- `Sigil: play KNEXT round locally`
- `Sigil: canonicalize Dokumenta project locally`
- `Sigil: build standalone container`
- `Sigil: clear workflows in container`
- `Sigil: canonicalize Dokumenta project in container`

## Boundary

`virtual-rpm/sigil-quarto-actions.virtual-rpm.json` records the typed package
intent. It is not an installer and it does not grant authority. Chocolatey,
Docker, and any repository operation are separate human-authorized steps.

The container is the thin Quazris path:

```text
sigil-quarto-actions
-> clear-workflows
-> local sigilbook anchors
-> Koko SDK / KLI / QLI source compatibility
-> bounded 0..3 workflow witness
-> play-knext-round
-> Pydantika Aprende / deploy-plan / merge-plan / PACAIOGAME witness
-> canonicalize-dokumenta
-> PACA Dokumenta V6 / PACA Pandoc / PACA Quarto project-management witness
```

Thick Sigil subsystems still live in main `sigilbook` and bind `sigil4py` plus
`sigil4cpython`; this container only checks their source anchors.
