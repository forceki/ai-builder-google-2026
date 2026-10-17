from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]


def _config(db: Path) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db.as_posix()}")
    cfg.attributes["configure_logger"] = False
    return cfg


def test_migrations_match_the_models(tmp_path):
    cfg = _config(tmp_path / "migrated.db")
    command.upgrade(cfg, "head")
    command.check(cfg)


def test_migrations_downgrade_to_empty(tmp_path):
    cfg = _config(tmp_path / "roundtrip.db")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
