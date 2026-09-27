"""Command-line entry point: ``mirrored <command>``.

Exit codes: 0 on success (upstream outages are reported as warnings), 1 when
the run could not do its job at all, 2 for configuration errors.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from mirrored import aio, catalog, convert, gha, releases, scripts
from mirrored.config import ConfigError, load_aio, load_modules, load_releases
from mirrored.files import changed_files, snapshot
from mirrored.http import make_session


def cmd_sync_releases(args: argparse.Namespace) -> int:
    sources = load_releases(args.root / args.config)
    if args.only:
        sources = [s for s in sources if s.name in args.only]
        if not sources:
            raise ConfigError(f"no source named {', '.join(args.only)}")

    api = make_session()
    api.headers["Accept"] = "application/vnd.github+json"
    api.headers["X-GitHub-Api-Version"] = "2022-11-28"
    if token := os.environ.get("GITHUB_TOKEN"):
        api.headers["Authorization"] = f"Bearer {token}"
    # Asset downloads redirect to a CDN that rejects API tokens, so use a bare session.
    downloads = make_session()

    results = []
    for source in sources:
        with gha.group(f"Sync {source.name}"):
            results += releases.sync_source(source, root=args.root, api=api, downloads=downloads)
    releases.report(results)

    for result in results:
        for path in result.updated:
            print(f"updated {path}")
    if results and all(r.error for r in results):
        gha.error("Every upstream release failed to sync; check the token and network.")
        return 1
    return 0


def _env_list(*names: str) -> list[str]:
    return [value for name in names if (value := os.environ.get(name, "").strip())]


def cmd_build_modules(args: argparse.Namespace) -> int:
    config = load_modules(args.root / args.config)

    proxy_base = (
        args.proxy_base if args.proxy_base is not None else os.environ.get("PROXY_BASE", "")
    ).strip()
    proxy_hosts = config.convert.proxy_hosts
    modules_dir = args.root / config.convert.output_dir
    # Converted modules briefly hold upstream script links until the mirroring
    # step rewrites them, so real changes are measured across the whole command.
    before = snapshot(modules_dir, "*.sgmodule")

    if not args.skip_convert:
        catalog_urls = (
            args.catalog_url
            or _env_list("LIST_URL_PRIMARY", "LIST_URL_BACKUP")
            or list(config.catalog.urls)
        )
        try:
            with gha.group("Download plugin catalog"):
                payload = catalog.download_catalog(catalog_urls)
                plugin_urls = catalog.extract_plugin_urls(payload, config.catalog.extensions)
                print(f"Found {len(plugin_urls)} plugins")
            if not plugin_urls:
                raise catalog.CatalogError("catalog contains no plugin URLs")
        except catalog.CatalogError as exc:
            gha.warning(f"Skipping plugin conversion: {exc}")
        else:
            fetch_session = make_session(user_agent=config.convert.user_agent)
            # Conversion errors are deterministic, so Script-Hub calls are not retried.
            scripthub = make_session(retries=0)
            with gha.group("Convert plugins via Script-Hub"):
                convert.wait_for_scripthub(scripthub, config.convert.scripthub_url)
                results = convert.convert_all(
                    fetch_session,
                    scripthub,
                    plugin_urls,
                    root=args.root,
                    config=config.convert,
                    proxy_base=proxy_base,
                )
                for r in results:
                    print(f"{r.status:>9}  {r.name}  {r.via}  {r.detail}".rstrip())
            convert.report(results)

    with gha.group("Mirror external scripts"):
        session = make_session(user_agent=config.scripts.user_agent)
        script_results = scripts.mirror_scripts(
            session,
            root=args.root,
            modules_dir=modules_dir,
            config=config.scripts,
            proxy_base=proxy_base,
            proxy_hosts=proxy_hosts,
        )
        for r in script_results:
            print(f"{r.status:>9}  {r.filename}  {r.detail}".rstrip())
    scripts.report(script_results)

    changed = changed_files(before, snapshot(modules_dir, "*.sgmodule"))
    names = ", ".join(p.name for p in changed) or "none"
    gha.summary(f"## Changed modules\n\n{len(changed)} changed: {names}")
    return 0


def cmd_build_aio(args: argparse.Namespace) -> int:
    config = load_aio(args.root / args.config)
    try:
        changed = aio.build(args.root, config, date=args.date)
    except aio.MissingSourceError as exc:
        gha.error(f"All-in-One not rebuilt; missing source modules: {exc}")
        return 1
    for path, did_change in changed.items():
        print(f"{'updated' if did_change else 'unchanged':>9}  {path}")
    gha.set_output("changed", "true" if any(changed.values()) else "false")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mirrored", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", type=Path, default=Path(), help="repository root (default: current directory)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sync-releases", help="mirror assets from upstream GitHub releases")
    p.add_argument("--config", default="config/releases.yaml")
    p.add_argument("--only", action="append", metavar="NAME", help="limit to these sources")
    p.set_defaults(func=cmd_sync_releases)

    p = sub.add_parser("build-modules", help="convert plugins and mirror their scripts")
    p.add_argument("--config", default="config/modules.yaml")
    p.add_argument("--catalog-url", action="append", help="override the catalog URLs (repeatable)")
    p.add_argument(
        "--proxy-base", help="fallback proxy prefix for proxy_hosts (default: $PROXY_BASE)"
    )
    p.add_argument(
        "--skip-convert", action="store_true", help="only mirror scripts of existing modules"
    )
    p.set_defaults(func=cmd_build_modules)

    p = sub.add_parser("build-aio", help="rebuild the All-in-One module and reject ruleset")
    p.add_argument("--config", default="config/aio.yaml")
    p.add_argument("--date", help="override the Update: date (MM/DD/YYYY)")
    p.set_defaults(func=cmd_build_aio)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        gha.error(f"Configuration error: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
