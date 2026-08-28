# SIGILITAS piBI PACADEX v1

This subsystem maps accepted GitHub project events into a read-only, typed PACADEX snapshot.

```text
accepted main commit or published release
→ GitHubProjectType
→ piBI SessionTree
→ source-bound RAG inspection
→ global policy gate
→ PACADEX
→ MCP resource manifest
→ immutable workflow artifact
```

## Failure audit boundary

No PR-triggered workflow runs were visible for the current fork head during the source audit. Therefore this integration does not label a source or test as failed. It records observable static risks instead:

- mutable action tags in existing workflows;
- inconsistent checkout major versions across workflow examples;
- a latest-download dependency without a digest;
- write permission in the publish test;
- no existing Dependabot configuration for GitHub Actions.

The new workflow pins external actions to full commit SHAs, uses read-only repository permissions, disables checkout credential persistence and emits artifacts without committing generated state.

## Release management

Action publishers use semantic release tags and may maintain a major compatibility alias such as `v2`. Consumers that prioritize reviewed immutability use a full commit SHA. A release-specific immutable tag such as `v2.2.0` is never reused or moved; a moving major alias is not treated as an immutable release tag.

## piBI sessions

The additive bunch `&` shares event and global-policy context. The multiplicative bunch `*` separates PACADEX construction from MCP projection so their capabilities do not alias. Every KOKOMPI remains identity-distinct and receives one bounded effect.

MCP exposure is descriptive: resources are generated, but no server, workflow dispatch, merge, release or tag move is granted by this carrier.
