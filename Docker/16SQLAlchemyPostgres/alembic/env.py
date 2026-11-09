"""Ambiente Alembic: collega le migrazioni al database e ai modelli dell'applicazione."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import DATABASE_URL
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# i metadati dei modelli: servono a "alembic revision --autogenerate" e "alembic check"
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """alembic upgrade head --sql : stampa l'SQL senza collegarsi al database."""
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
