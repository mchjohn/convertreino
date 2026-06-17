"""Add Strava OAuth fields to users."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("strava_athlete_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("access_token", sa.String(length=512), nullable=True))
    op.add_column("users", sa.Column("refresh_token", sa.String(length=512), nullable=True))
    op.add_column(
        "users",
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_users_strava_athlete_id", "users", ["strava_athlete_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_strava_athlete_id", "users", type_="unique")
    op.drop_column("users", "token_expires_at")
    op.drop_column("users", "refresh_token")
    op.drop_column("users", "access_token")
    op.drop_column("users", "strava_athlete_id")
