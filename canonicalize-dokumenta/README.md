# Canonicalize Dokumenta

`canonicalize-dokumenta` binds main `sigilbook` PACA Dokumenta V6 to a resident
PACA Pandoc / PACA Quarto project-management source plan.

It checks local source anchors for:

- `SIGILITAS_PACA_DOKUMENTA_VERSION_CONTROL_HYPERDAG_V6`
- Sigil/Sigilitas version bindings for consolidacion
- PACA Pandoc and PACA Quarto render-plan markers
- protected Pi canon
- append-only version-control and Safe Replay invariants
- an optional admitted `clear-workflows` witness

It does not call the GitHub API, run `gh`, dispatch workflows, mutate Git,
execute Pandoc, execute Quarto, start schedulers, or perform provider IO.

## Local Run

```bash
python clear-workflows/sigil_workflow_clear.py \
  --sigilbook-path ../sigilbook \
  --resident-path . \
  --workflow-layer examples \
  --resident-manifest examples/synthgothhub-residents.example.json \
  --witness-output sigil-clearance-witness.local.json \
  --fail-on-hold false

python canonicalize-dokumenta/sigil_dokumenta_project.py \
  --sigilbook-path ../sigilbook \
  --resident-path . \
  --project-path . \
  --clearance-witness sigil-clearance-witness.local.json \
  --witness-output sigil-dokumenta-project-witness.local.json \
  --project-id paca.dokumenta.sigil-quarto-actions.local \
  --fail-on-hold false
```

`ADMIT_SOURCE_PLAN` means the project-management plan is canonically typed as
source evidence. It is not a claim that Quarto or Pandoc rendered anything.
