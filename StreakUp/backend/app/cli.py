"""
CLI commands for backend operational tasks.

Responsibility:
- Expose deploy-safe bootstrap and migration commands.
"""

import json
from pathlib import Path

import click

from app.services.catalog_bootstrap_service import seed_catalog
from app.services.legacy_sqlite_migration_service import audit_legacy_sqlite, migrate_legacy_sqlite


def register_cli_commands(app) -> None:
    """Register custom Flask CLI commands."""

    @app.cli.command("seed-catalog")
    def seed_catalog_command() -> None:
        """Seed the default habit catalog without demo users."""
        summary = seed_catalog()
        click.echo(
            "Catalog ready. "
            f"categories_created={summary['categories_created']} "
            f"habits_created={summary['habits_created']} "
            f"total_categories={summary['total_categories']} "
            f"total_habits={summary['total_habits']}"
        )

    @app.cli.command("audit-legacy-sqlite")
    @click.option(
        "--path",
        "sqlite_path",
        required=True,
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help="Path to the legacy SQLite file to inspect.",
    )
    def audit_legacy_sqlite_command(sqlite_path: Path) -> None:
        """Audit a legacy SQLite file before migrating it."""
        report = audit_legacy_sqlite(sqlite_path)
        click.echo(json.dumps(report, indent=2, sort_keys=True))

    @app.cli.command("migrate-sqlite-to-postgres")
    @click.option(
        "--path",
        "sqlite_path",
        required=True,
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help="Path to the legacy SQLite file to import into the current database.",
    )
    def migrate_sqlite_to_postgres_command(sqlite_path: Path) -> None:
        """Import a legacy SQLite file into the current database."""
        summary = migrate_legacy_sqlite(sqlite_path)
        click.echo(json.dumps(summary, indent=2, sort_keys=True))
