import json

from app import config


def test_available_models_parses_opencode_config(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "provider": {
            "deepseek": {
                "models": {
                    "deepseek-v4-flash": {},
                    "deepseek-v4-pro": {},
                }
            },
            "sp-ollama": {
                "models": {
                    "qwen2.5:0.5b": {},
                }
            }
        }
    }))

    monkeypatch.setattr(config, "OPENCODE_CONFIG_PATH", str(config_file))

    assert config.available_models() == [
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
        "sp-ollama/qwen2.5:0.5b",
    ]


def test_available_models_returns_empty_when_config_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OPENCODE_CONFIG_PATH", str(tmp_path / "missing.json"))

    assert config.available_models() == []


def test_model_is_available(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "provider": {
            "deepseek": {
                "models": {
                    "deepseek-v4-flash": {},
                }
            }
        }
    }))

    monkeypatch.setattr(config, "OPENCODE_CONFIG_PATH", str(config_file))

    assert config.model_is_available("deepseek/deepseek-v4-flash")
    assert not config.model_is_available("deepseek/not-a-model")
