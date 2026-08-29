# Github Actions for Quarto

This repository stores [Github Actions](https://github.com/features/actions) useful for building and publishing [Quarto](https://quarto.org/) documents.

1. [quarto-dev/quarto-actions/setup](./setup) - Install Quarto
2. [quarto-dev/quarto-actions/render](./render) - Render project
3. [quarto-dev/quarto-actions/publish](./publish) - Publish project
4. [jbermejovega/sigil-quarto-actions/clear-workflows](./clear-workflows) - Clear localized Sigil editorial workflow layers against a local main `sigilbook` and Koko SDK source witness
5. [jbermejovega/sigil-quarto-actions/play-knext-round](./play-knext-round) - Play a bounded Pydantika Aprende / deploy-plan / merge-plan / PACAIOGAME KNEXT source round
6. [jbermejovega/sigil-quarto-actions/canonicalize-dokumenta](./canonicalize-dokumenta) - Canonicalize PACA Dokumenta V6 project management for PACA Pandoc and PACA Quarto as a source plan

We recommend using `v2` for your actions, and our examples all use `v2`.

## Examples

In [Examples](./examples), you will find a YAML workflow file to serve as a template to be reused as a base for your project. We are also sharing some links to real example Github repositories using Quarto with Github Actions for rendering and deploying documents and projects. If you want to add your repository in the list, we welcome a PR.

## Sigil Editorial Curation

`clear-workflows` turns this repository into a thin Sigil subsystem for the
editorial-curatorial localized layer. It does not call the GitHub API, dispatch
workflows, merge, push, or fetch `sigilbook`; it reads a local `sigilbook`
checkout and emits a typed compatibility witness for the Sigil KLI/QLI/CLI and
Codex GitHub connector layer.

For local Windows/VS Code setup with Chocolatey and a standalone devcontainer,
see [setup/VS_CODE_STANDALONE_SIGIL_SYSTEM.md](./setup/VS_CODE_STANDALONE_SIGIL_SYSTEM.md).

`play-knext-round` composes the admitted clearance witness with local main
`sigilbook` PACAIOGAME and KNEXT IR anchors. Deploy and merge remain typed
plans, not external execution.

`canonicalize-dokumenta` composes the admitted clearance witness with local main
`sigilbook` PACA Dokumenta V6 anchors, then reconciles Sigil/Sigilitas versions
into a consolidation map. PACA Pandoc and PACA Quarto are managed as project
lanes and render plans; Pandoc and Quarto are not executed by the carrier.

## Release Management

This repository uses [GitHub's recommended release management for actions](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-release-management-for-actions): 

* GitHub releases with tags are used for updates on the actions. 
* Semantic versioning is used, with major, minor and possibly patch release. 
* Major versions (such as `v1`) will always point to the last minor or patch release for this major version. (when `v1.0.2` is out, `v1` will point to this update, too). This means using `quarto-dev/quarto-actions/setup@v2` in your workflow file will automatically get the updated versions. Using `quarto-dev/quarto-actions/setup@v1.0.2` will pin a specific release.
* Major version changes (`v1` to `v2`) will often come with breaking changes, and workflows might require manual updates.
