# SIGILITAS whole PR tree typing

`SIGILITAS_WHOLE_PR_TREE_TYPED_V1` types every materialized file in the checked-out project tree. Directories are explicit containment nodes and files preserve their own identities, content digests, artifact types, and capability scopes.

Known surfaces receive specialized types. An unfamiliar extension remains visible as `PrimitiveArtifactType`; it is never silently discarded. Symlinks and generated runtime directories are outside the source tree projection.

The containment tree is the structural presentation. The executable projection is a bounded acyclic `DAG<FluxQuantumTyped>` with one `TYPE_ARTIFACT` effect per file. These presentations are related but are not identified.

The piBI session shares project context and provenance additively with `&`, while file resources remain identity-distinct under multiplicative `*`. The output is read-only, Safe Replay capable, and grants no GitHub or runtime authority.
