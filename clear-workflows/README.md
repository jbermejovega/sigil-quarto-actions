# Clear Sigil Editorial Workflows

`clear-workflows` is the thin editorial-curatorial subsystem for
`sigil-quarto-actions`. It validates a resident repository's localized workflow
layer against an already-materialized main `sigilbook` checkout and the Koko SDK
KLI/QLI anchors.

The checker is deliberately local:

- no GitHub API calls;
- no `gh api`, workflow dispatch, rerun, merge, or push;
- no `actions/checkout` of main `sigilbook`;
- no package installation;
- Python standard library only.

Repository operations stay outside this carrier. In the Sigil stack, the
Sigil KLI/QLI/CLI and the Codex GitHub connector own the typed plan and any
human-authorized repository action. This action only emits the source witness.
Connector-visible `sigilbook/main` may clear as `baseline`; local overlays that
also expose the exact KLI/QLI pyproject entrypoint clear as `extended`.

## Usage

```yaml
steps:
  - name: Check out resident repository
    uses: actions/checkout@v6
    with:
      persist-credentials: false

  - name: Materialize main sigilbook through Sigil KLI/QLI
    run: test -d .sigilbook

  - name: Clear localized editorial workflows
    uses: jbermejovega/sigil-quarto-actions/clear-workflows@v2
    with:
      sigilbook-path: .sigilbook
      workflow-layer: .github/workflows
      subsystem-mode: thin
      max-fanin: 3
      max-fanout: 3
      max-layer: 3
```

For local Codex runs from this repository:

```bash
python clear-workflows/sigil_workflow_clear.py \
  --sigilbook-path ../sigilbook \
  --resident-path . \
  --workflow-layer examples \
  --witness-output sigil-clearance-witness.local.json
```

## Verdicts

- `ADMIT_SOURCE_PLAN`: anchors are present and workflow job graphs stay within
  the bounded 0-1-2-3 fan contract.
- `HOLD`: the checker found an incomplete local witness, such as a missing
  workflow layer or unknown `needs` edge.
- `REJECT`: the checker found forbidden authority or an over-budget graph.

## Thin And Thick Modes

`thin` mode is Quazris-shaped: local files, minimal dependencies, and bounded
workflow fan-in/fan-out. It does not emit or execute MLIR bytecode.

`thick` mode additionally requires `sigil4py` and `sigil4cpython` source anchors
in main `sigilbook`, while still leaving runtime startup and repository mutation
outside this checker.
