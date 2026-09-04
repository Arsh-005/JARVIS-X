from __future__ import annotations

import os
from pathlib import Path


class SecretProvider:
    def get(self, name: str, default: str = "") -> str:
        raise NotImplementedError


class EnvironmentSecretProvider(SecretProvider):
    def get(self, name: str, default: str = "") -> str:
        return os.getenv(name, default)


class FileSecretProvider(SecretProvider):
    """Supports Docker/Kubernetes mounted secrets without baking credentials into images."""

    def __init__(self, directory: str | Path = "/run/secrets") -> None:
        self.directory = Path(directory)

    def get(self, name: str, default: str = "") -> str:
        path = self.directory / name
        return path.read_text(encoding="utf-8").strip() if path.exists() else default
