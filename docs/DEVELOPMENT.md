# Development

Maintainer notes for the automation behind Mirrored. Users only need the
[README](../README.md) and the [Chinese index](../README.zh-CN.md).

## Repository layout

| Path | Contents | Produced by |
|------|----------|-------------|
| `BiliUniverse/` | Bilibili modules from [BiliUniverse](https://github.com/BiliUniverse) releases | `sync-releases` |
| `DualSubs/` | Dual-language subtitle modules from [DualSubs](https://github.com/DualSubs) releases | `sync-releases` |
| `iRingo/` | Apple service modules from [NSRingo](https://github.com/NSRingo) releases, split into `plugin/`, `sgmodule/`, `snippet/`, `stoverride/` | `sync-releases` |
| `Chores/sgmodule/` | Surge modules converted from the Loon plugin catalog, plus the combined `All-in-One-2.x.sgmodule` | `build-modules`, `build-aio` |
| `Chores/js/` | Mirrored copies of the scripts those modules load | `build-modules` |
| `Chores/ruleset/reject.list` | Reject rules merged from the All-in-One sources | `build-aio` |
| `config/` | What to mirror and how (see below) | — |
| `src/mirrored/` | The Python tooling behind every workflow | — |

Files under the output directories are generated; edit `config/` instead.

---

## Automation

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| [`sync-releases.yml`](../.github/workflows/sync-releases.yml) | every 25 min | Mirrors the latest release assets of the repositories in `config/releases.yaml`. Renamed upstream repositories are followed automatically. Files upstream no longer publishes are listed in the job summary; run it manually with `prune` to delete them. |
| [`build-modules.yml`](../.github/workflows/build-modules.yml) | every 25 min, and on config changes | Downloads every plugin in the catalog (directly with a Surge User-Agent, falling back to `PROXY_BASE`), converts them through a local Script-Hub container, mirrors external scripts the same way, rebuilds the All-in-One module and notifies `bunizao/TutuBetterRules` when it changes. Pull requests touching the pipeline get a full dry run. |
| [`ci.yml`](../.github/workflows/ci.yml) | pull requests | Ruff, pytest and actionlint. |

Upstream outages show up as warnings and in each run's job summary; they never delete existing files. A run only fails when it cannot do its job at all (for example, every upstream failed or an All-in-One source is missing).

Workflows started manually from a branch other than `main` are dry runs: they report what would change without pushing.

Repository settings used by `build-modules`:

| Name | Kind | Purpose |
|------|------|---------|
| `PROXY_BASE` | variable | Fallback prefix for plugin and script downloads when the direct request fails, e.g. `https://proxy.example/?url=` |
| `LIST_URL_PRIMARY`, `LIST_URL_BACKUP` | variables | Override the plugin catalog URL (default in `config/modules.yaml`) |
| `DISPATCH_TOKEN` | secret | Token allowed to send `repository_dispatch` to `bunizao/TutuBetterRules` |

---

## Configuration

- [`config/releases.yaml`](../config/releases.yaml) – upstream repositories, where each asset type goes, extra files and forced module arguments.
- [`config/modules.yaml`](../config/modules.yaml) – plugin catalog, Script-Hub conversion and script mirroring settings.
- [`config/index.yaml`](../config/index.yaml) – layout of the Chinese index page `README.zh-CN.md`, built from the plugin catalog metadata (`Chores/catalog.json`) and each file's own header.
- [`config/aio.yaml`](../config/aio.yaml) – modules merged into `All-in-One-2.x.sgmodule`, rendered with [`config/templates/`](../config/templates).

---

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                   # install dependencies
uv run mirrored sync-releases --only DualSubs
uv run mirrored build-aio
uv run mirrored build-index                    # regenerate the Chinese index page
docker run -d --rm --network host xream/script-hub   # Script-Hub on :9101 for build-modules
uv run mirrored build-modules
uv run pytest && uv run ruff check && uv run ruff format --check && uv run actionlint
```
