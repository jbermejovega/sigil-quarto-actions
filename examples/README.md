# Using Quarto Actions: Examples

* [Basics](./example-01-basics.md)
* [Freeze](./example-02-freeze.md)
* [Dependencies](./example-03-dependencies.md)
* [Render with no publish](./example-04-render-no-publish.md)
* [Rendering and publishing a non-top-level project](./example-05-non-top-level.md)
* [Publishing a single format, publishing without rendering](./example-06-no-render.md)
* [Publishing a single format](./example-07-publish-single-format.md)
* [Publishing to other services](./example-08-publish-to-others-services.md)
* [Sigil editorial curation clearance](./sigil-editorial-curation-clearance.yml)
* [Sigil PACAIOGAME KNEXT round](./sigil-pacaiogame-knext-round.yml)
* [Sigil PACA Dokumenta project management](./sigil-paca-dokumenta-project-management.yml)

## Sigil examples

The Sigil example keeps main `sigilbook` materialization outside GitHub API
actions. The local KLI/QLI/CLI or Codex GitHub connector layer must provide the
`sigilbook` source path before `clear-workflows` validates the resident
workflow layer.
The KNEXT round example then consumes that clearance witness to emit a
Pydantika Aprende / deploy-plan / merge-plan / PACAIOGAME source-play receipt.
The Dokumenta example consumes the same clearance witness and binds main
`sigilbook` PACA Dokumenta V6 to a bounded PACA Pandoc / PACA Quarto
project-management witness without rendering documents.

## Repositories using Quarto actions

- [Earthdata Cloud Cookbook](https://nasa-openscapes.github.io/earthdata-cloud-cookbook/) ([source](https://github.com/NASA-Openscapes/earthdata-cloud-cookbook), [workflow file](https://github.com/NASA-Openscapes/earthdata-cloud-cookbook/blob/main/.github/workflows/quarto-publish.yml)) This book contains `.md` and `.ipynb` files, and is built with Quarto and Python in GHA, and deployed to Github Pages. 

- [R Manuals Quarto website](https://rstudio.github.io/r-manuals/) ([source](https://github.com/rstudio/r-manuals), [workflow file](https://github.com/rstudio/r-manuals/blob/main/.github/workflows/build-website.yaml)) This project uses a workflow to build several books with R and Quarto and organizes them in a website deployed to Github pages.

- [Pathology Atlas](https://www.patolojiatlasi.com/EN) ([source](https://github.com/patolojiatlasi/patolojiatlasi.github.io), [workflow file](https://github.com/patolojiatlasi/patolojiatlasi.github.io/blob/main/.github/workflows/Quarto-Render-Bilingual-Book-Push-Other-Repos-GitLab.yml)) This multilingual website is rendered in two versions and deployed using Github Actions. 

## FAQ

* My project uses git lfs storage; how should I adapt the action?

  If your project uses git lfs storage, you must opt-in to git lfs during the `checkout` step.

  ```yaml
        - name: Check out repository
          uses: actions/checkout@v6
          with:
            lfs: true # needed when using lfs for image storage
  ```

  See the [checkout action documentation](https://github.com/actions/checkout) for details.
