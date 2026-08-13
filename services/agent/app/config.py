import os
from pathlib import Path
from typing import Optional

PROVIDER = os.getenv("OPENCODE_PROVIDER", "deepseek")
MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")
WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
ARTIFACT_ROOT = Path(os.getenv("ARTIFACT_ROOT", "/artifacts"))
QUEUE_NAME = "jobs"

AVAILABLE_MODELS = tuple(
    model.strip()
    for model in os.getenv(
        "OPENCODE_MODELS",
        "deepseek/deepseek-v4-flash,deepseek/deepseek-v4-pro,sp-ollama/qwen2.5:0.5b",
    ).split(",")
    if model.strip()
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "software_press")
POSTGRES_USER = os.getenv("POSTGRES_USER", "sp_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sp_password")


def opencode_model() -> str:
    return f"{PROVIDER}/{MODEL}"


def resolve_model(model: Optional[str] = None) -> str:
    selected = model or opencode_model()
    if selected not in AVAILABLE_MODELS:
        raise ValueError(f"model {selected} is not available")
    return selected
