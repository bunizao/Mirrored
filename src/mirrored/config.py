"""Typed loaders for the YAML files under ``config/``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when a config file is missing required keys or has the wrong shape."""


def _load(path: Path) -> Mapping[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{path}: file not found") from exc
    if not isinstance(data, Mapping):
        raise ConfigError(f"{path}: expected a mapping at the top level")
    return data


def _str(data: Mapping[str, Any], key: str, where: str) -> str:
    value = data.get(key)
    if value is None or isinstance(value, (Mapping, list)):
        raise ConfigError(f"{where}: '{key}' must be a string")
    # YAML turns values such as `12306` into ints; everything here is text.
    return str(value)


def _str_list(data: Mapping[str, Any], key: str, where: str) -> tuple[str, ...]:
    value = data.get(key) or []
    if not isinstance(value, list):
        raise ConfigError(f"{where}: '{key}' must be a list")
    return tuple(str(item) for item in value)


def _str_map(data: Mapping[str, Any], key: str, where: str) -> dict[str, str]:
    value = data.get(key) or {}
    if not isinstance(value, Mapping):
        raise ConfigError(f"{where}: '{key}' must be a mapping")
    return {str(k): str(v) for k, v in value.items()}


# --- releases.yaml ---------------------------------------------------------


@dataclass(frozen=True)
class ExtraFile:
    url: str
    path: str


@dataclass(frozen=True)
class ReleaseSource:
    name: str
    repos: tuple[str, ...]
    # File extension (without the dot) -> destination directory.
    routes: Mapping[str, str]
    extra_files: tuple[ExtraFile, ...] = ()
    # File extension -> {argument name: forced default value}.
    argument_overrides: Mapping[str, Mapping[str, str]] = field(default_factory=dict)


def load_releases(path: Path) -> list[ReleaseSource]:
    data = _load(path)
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ConfigError(f"{path}: 'sources' must be a non-empty list")

    result = []
    for index, raw in enumerate(sources):
        where = f"{path}: sources[{index}]"
        if not isinstance(raw, Mapping):
            raise ConfigError(f"{where}: expected a mapping")
        routes = _str_map(raw, "routes", where)
        if not routes:
            raise ConfigError(f"{where}: 'routes' must not be empty")
        extras = []
        for j, extra in enumerate(raw.get("extra_files") or []):
            extra_where = f"{where}.extra_files[{j}]"
            if not isinstance(extra, Mapping):
                raise ConfigError(f"{extra_where}: expected a mapping")
            extras.append(
                ExtraFile(
                    url=_str(extra, "url", extra_where), path=_str(extra, "path", extra_where)
                )
            )
        overrides_raw = raw.get("argument_overrides") or {}
        if not isinstance(overrides_raw, Mapping):
            raise ConfigError(f"{where}: 'argument_overrides' must be a mapping")
        overrides = {
            str(ext): _str_map(overrides_raw, ext, f"{where}.argument_overrides")
            for ext in overrides_raw
        }
        result.append(
            ReleaseSource(
                name=_str(raw, "name", where),
                repos=_str_list(raw, "repos", where),
                routes=routes,
                extra_files=tuple(extras),
                argument_overrides=overrides,
            )
        )
    return result


# --- modules.yaml ----------------------------------------------------------


@dataclass(frozen=True)
class CatalogConfig:
    urls: tuple[str, ...]
    extensions: tuple[str, ...]


@dataclass(frozen=True)
class ConvertConfig:
    output_dir: str
    scripthub_url: str
    category: str
    user_agent: str
    proxy_hosts: tuple[str, ...]


@dataclass(frozen=True)
class ScriptsConfig:
    output_dir: str
    mirror_base: str
    user_agent: str
    skip_patterns: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True)
class ModulesConfig:
    catalog: CatalogConfig
    convert: ConvertConfig
    scripts: ScriptsConfig


def _section(data: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ConfigError(f"{where}: '{key}' must be a mapping")
    return value


def load_modules(path: Path) -> ModulesConfig:
    data = _load(path)
    where = str(path)
    catalog = _section(data, "catalog", where)
    convert = _section(data, "convert", where)
    scripts = _section(data, "scripts", where)
    return ModulesConfig(
        catalog=CatalogConfig(
            urls=_str_list(catalog, "urls", f"{where}: catalog"),
            extensions=_str_list(catalog, "extensions", f"{where}: catalog"),
        ),
        convert=ConvertConfig(
            output_dir=_str(convert, "output_dir", f"{where}: convert"),
            scripthub_url=_str(convert, "scripthub_url", f"{where}: convert"),
            category=_str(convert, "category", f"{where}: convert"),
            user_agent=_str(convert, "user_agent", f"{where}: convert"),
            proxy_hosts=_str_list(convert, "proxy_hosts", f"{where}: convert"),
        ),
        scripts=ScriptsConfig(
            output_dir=_str(scripts, "output_dir", f"{where}: scripts"),
            mirror_base=_str(scripts, "mirror_base", f"{where}: scripts").rstrip("/"),
            user_agent=_str(scripts, "user_agent", f"{where}: scripts"),
            skip_patterns=_str_list(scripts, "skip_patterns", f"{where}: scripts"),
            exclude=_str_list(scripts, "exclude", f"{where}: scripts"),
        ),
    )


# --- aio.yaml --------------------------------------------------------------


@dataclass(frozen=True)
class AioSource:
    path: str
    header: str


@dataclass(frozen=True)
class AioConfig:
    template: str
    output: str
    ruleset: str
    sources: tuple[AioSource, ...]


def load_aio(path: Path) -> AioConfig:
    data = _load(path)
    where = str(path)
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ConfigError(f"{where}: 'sources' must be a non-empty list")
    parsed = []
    for index, raw in enumerate(sources):
        item_where = f"{where}: sources[{index}]"
        if not isinstance(raw, Mapping):
            raise ConfigError(f"{item_where}: expected a mapping")
        parsed.append(
            AioSource(path=_str(raw, "path", item_where), header=_str(raw, "header", item_where))
        )
    return AioConfig(
        template=_str(data, "template", where),
        output=_str(data, "output", where),
        ruleset=_str(data, "ruleset", where),
        sources=tuple(parsed),
    )
