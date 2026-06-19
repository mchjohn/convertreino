from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[3]


def load_env() -> None:
    env_file = BACKEND_ROOT / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


load_env()
