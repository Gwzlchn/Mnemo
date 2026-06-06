"""tests for shared/config.py"""

import os
from pathlib import Path

import pytest

from shared.config import (
    AppConfig,
    build_step_config,
    load_config,
    load_domain_profile,
    load_yaml,
    resolve_env_vars,
)


class TestResolveEnvVars:
    def test_simple_var(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "secret123")
        assert resolve_env_vars("key=${MY_KEY}") == "key=secret123"

    def test_var_with_default_uses_value(self, monkeypatch):
        monkeypatch.setenv("MY_KEY", "actual")
        assert resolve_env_vars("${MY_KEY:-fallback}") == "actual"

    def test_var_with_default_missing(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        assert resolve_env_vars("${MISSING_VAR:-fallback}") == "fallback"

    def test_var_with_empty_default(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        assert resolve_env_vars("${MISSING_VAR:-}") == ""

    def test_missing_no_default_preserved(self, monkeypatch):
        monkeypatch.delenv("UNDEFINED_VAR", raising=False)
        assert resolve_env_vars("${UNDEFINED_VAR}") == "${UNDEFINED_VAR}"

    def test_multiple_vars(self, monkeypatch):
        monkeypatch.setenv("A", "1")
        monkeypatch.setenv("B", "2")
        assert resolve_env_vars("${A}-${B}") == "1-2"

    def test_no_vars(self):
        assert resolve_env_vars("plain text") == "plain text"


class TestLoadYaml:
    def test_load_valid(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PORT", "8080")
        f = tmp_path / "test.yaml"
        f.write_text("server:\n  port: ${PORT}\n  host: localhost\n")
        result = load_yaml(f)
        assert result == {"server": {"port": 8080, "host": "localhost"}}

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_yaml(tmp_path / "nonexistent.yaml")

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert load_yaml(f) == {}

    def test_env_in_string(self, tmp_path, monkeypatch):
        monkeypatch.setenv("API_KEY", "sk-123")
        f = tmp_path / "test.yaml"
        f.write_text('api_key: "${API_KEY}"\n')
        result = load_yaml(f)
        assert result["api_key"] == "sk-123"


class TestLoadConfig:
    def test_loads_from_configs_dir(self, configs_dir, tmp_data_dir):
        cfg = load_config(config_dir=configs_dir, data_dir=tmp_data_dir)
        assert isinstance(cfg, AppConfig)
        assert cfg.db_path == tmp_data_dir / "db" / "analyzer.db"
        assert cfg.jobs_dir == tmp_data_dir / "jobs"
        assert "video" in cfg.pipelines
        assert "paper" in cfg.pipelines
        assert "pools" in cfg.pools
        assert "providers" in cfg.providers

    def test_paths_correct(self, configs_dir, tmp_data_dir):
        cfg = load_config(config_dir=configs_dir, data_dir=tmp_data_dir)
        assert cfg.data_dir == tmp_data_dir
        assert cfg.config_dir == configs_dir
        assert cfg.prompts_dir == tmp_data_dir / "prompts"

    def test_missing_pipelines_raises(self, tmp_path, tmp_data_dir):
        with pytest.raises(FileNotFoundError):
            load_config(config_dir=tmp_path, data_dir=tmp_data_dir)


class TestLoadDomainProfile:
    def test_existing_domain(self, tmp_path):
        domain_dir = tmp_path / "domain"
        domain_dir.mkdir()
        (domain_dir / "deep-learning.yaml").write_text(
            "ocr:\n  confidence_threshold: 0.6\n"
        )
        result = load_domain_profile(tmp_path, "deep-learning")
        assert result == {"ocr": {"confidence_threshold": 0.6}}

    def test_missing_domain(self, tmp_path):
        result = load_domain_profile(tmp_path, "nonexistent")
        assert result == {}


class TestBuildStepConfig:
    def test_basic_structure(self, configs_dir, tmp_data_dir):
        cfg = load_config(config_dir=configs_dir, data_dir=tmp_data_dir)
        step_cfg = build_step_config(cfg, "video", "04_ocr", domain="deep-learning")

        assert step_cfg["step"]["name"] == "04_ocr"
        assert step_cfg["step"]["pool"] == "cpu"
        assert step_cfg["step"]["timeout_sec"] == 300
        assert step_cfg["step"]["retries"] == 2
        assert step_cfg["domain"]["name"] == "deep-learning"
        assert step_cfg["paths"]["data_dir"] == str(tmp_data_dir)

    def test_ai_config_included(self, configs_dir, tmp_data_dir):
        cfg = load_config(config_dir=configs_dir, data_dir=tmp_data_dir)
        step_cfg = build_step_config(cfg, "video", "08_smart")

        assert "primary" in step_cfg["ai"]
        assert step_cfg["ai"]["primary"]["provider"] == "anthropic"
        assert "text_fallback" in step_cfg["ai"]

    def test_no_ai_config(self, configs_dir, tmp_data_dir):
        cfg = load_config(config_dir=configs_dir, data_dir=tmp_data_dir)
        step_cfg = build_step_config(cfg, "video", "01_scene")

        assert step_cfg["ai"] == {}

    def test_invalid_step_raises(self, configs_dir, tmp_data_dir):
        cfg = load_config(config_dir=configs_dir, data_dir=tmp_data_dir)
        with pytest.raises(StopIteration):
            build_step_config(cfg, "video", "nonexistent_step")
