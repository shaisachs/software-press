import json
import os
from pathlib import Path
from typing import List

PROVIDER = os.getenv("OPENCODE_PROVIDER", "deepseek")
MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")
WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
ARTIFACT_ROOT = Path(os.getenv("ARTIFACT_ROOT", "/artifacts"))
QUEUE_NAME = "jobs"

OPENCODE_CONFIG_PATH = os.getenv(
    "OPENCODE_CONFIG_PATH", str(Path.home() / ".config/opencode/config.json")
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "software_press")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sp_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sp_password")


def opencode_model() -> str:
    return f"{PROVIDER}/{MODEL}"


def available_models() -> List[str]:
    try:
        with open(OPENCODE_CONFIG_PATH) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []

    models = []
    for provider, provider_cfg in data.get("provider", {}).items():
        for model in provider_cfg.get("models", {}):
            models.append(f"{provider}/{model}")
    return models


def model_is_available(model: str) -> bool:
    return model in available_models()
