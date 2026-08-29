# Play KNEXT Round

`play-knext-round` is a thin Sigil carrier for the phrase:

```text
PYDANTIKA APRENDE -> DEPLOY PLAN -> MERGE PLAN -> PACAIOGAME KNEXT ROUND
```

It consumes a `clear-workflows` witness, checks local main `sigilbook` anchors
for Koko SDK, KLI/QLI, PACAIOGAME typed actions and `KNEXT_PACAIOGAME_IR_M1`,
then emits a bounded play-round witness.

It does not:

- call the GitHub API;
- run `gh`;
- dispatch workflows;
- perform a Git merge;
- push refs;
- deploy packages or pages;
- start Godot or any game runtime.

Those operations remain external to this source carrier and must go through the
Sigil KLI/QLI/CLI plus Codex GitHub connector path with explicit authority.

## Local Run

```bash
python clear-workflows/sigil_workflow_clear.py \
  --sigilbook-path ../sigilbook \
  --resident-path . \
  --workflow-layer examples \
  --resident-manifest examples/synthgothhub-residents.example.json \
  --witness-output sigil-clearance-witness.local.json \
  --fail-on-hold false

python play-knext-round/sigil_knext_round.py \
  --sigilbook-path ../sigilbook \
  --resident-path . \
  --clearance-witness sigil-clearance-witness.local.json \
  --witness-output sigil-knext-round-witness.local.json \
  --round-id knext.pacaiogame.round.local \
  --fail-on-hold false
```

`ADMIT_SOURCE_PLAN` means the round is playable as a source witness. It is not a
claim that a deployment, merge, or live game execution happened.
