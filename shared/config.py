"""配置加载：YAML + 环境变量替换。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


_ENV_PATTERN = re.compile(r"\$\{(\w+)(?::-(.*?))?\}")


def resolve_env_vars(text: str) -> str:
    """替换 ${VAR} 和 ${VAR:-default} 格式的环境变量引用。
    - 有值：替换为环境变量值
    - 无值+有默认值：替换为默认值
    - 无值+无默认值：保留原文（运行时可能才需要）
    """

    def _replacer(match: re.Match) -> str:
        var_name = match.group(1)
        default = match.group(2)
        value = os.environ.get(var_name)
        if value is not None:
            return value
        if default is not None:
            return default
        return match.group(0)

    return _ENV_PATTERN.sub(_replacer, text)


def load_yaml(path: Path) -> dict:
    """加载 YAML 文件并替换环境变量。文件不存在抛 FileNotFoundError。"""
    text = path.read_text(encoding="utf-8")
    resolved = resolve_env_vars(text)
    return yaml.safe_load(resolved) or {}


def _load_optional(path: Path) -> dict:
    """加载可选 YAML，不存在返回空 dict。"""
    if path.exists():
        return load_yaml(path)
    return {}


@dataclass
class AppConfig:
    data_dir: Path
    db_path: Path
    jobs_dir: Path
    config_dir: Path
    prompts_dir: Path
    pipelines: dict
    pools: dict
    providers: dict


def load_config(
    config_dir: str | Path = "/data/configs",
    data_dir: str | Path = "/data",
) -> AppConfig:
    """一次性加载全部配置。"""
    config_dir = Path(config_dir)
    data_dir = Path(data_dir)
    return AppConfig(
        data_dir=data_dir,
        db_path=data_dir / "db" / "analyzer.db",
        jobs_dir=data_dir / "jobs",
        config_dir=config_dir,
        prompts_dir=data_dir / "prompts",
        pipelines=load_yaml(config_dir / "pipelines.yaml"),
        pools=load_yaml(config_dir / "pools.yaml"),
        providers=_load_optional(config_dir / "providers.yaml"),
    )


def load_domain_profile(config_dir: Path, domain: str) -> dict:
    """加载 domain/*.yaml，不存在返回空 dict。"""
    path = config_dir / "domain" / f"{domain}.yaml"
    return _load_optional(path)


def build_step_config(
    app_config: AppConfig,
    pipeline: str,
    step_name: str,
    domain: str = "general",
    style_tags: list[str] | None = None,
) -> dict:
    """Worker 调用：合并三层配置，返回传给步骤进程的 dict。"""
    pipeline_steps = app_config.pipelines[pipeline]["steps"]
    step_cfg = next(s for s in pipeline_steps if s["name"] == step_name)
    domain_cfg = load_domain_profile(app_config.config_dir, domain)

    return {
        "step": {
            "name": step_name,
            "pool": step_cfg["pool"],
            "timeout_sec": step_cfg.get("timeout_sec", 600),
            "retries": step_cfg.get("retries", 0),
        },
        "ai": step_cfg.get("ai", {}),
        "domain": {"name": domain, **domain_cfg},
        "style_tags": style_tags or [],
        "paths": {
            "data_dir": str(app_config.data_dir),
            "prompts_dir": str(app_config.prompts_dir),
            "config_dir": str(app_config.config_dir),
        },
        "providers": app_config.providers,
    }
