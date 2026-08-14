"""Configuracao do modelo."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_model: str


def get_settings() -> Settings:
    provider = os.getenv("LLM_PROVIDER")
    model = os.getenv("LLM_MODEL")

    if not provider:
        raise RuntimeError("Defina a variavel de ambiente LLM_PROVIDER.")
    if not model:
        raise RuntimeError("Defina a variavel de ambiente LLM_MODEL.")

    return Settings(llm_provider=provider, llm_model=model)
