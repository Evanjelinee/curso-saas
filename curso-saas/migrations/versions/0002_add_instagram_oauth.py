"""Добавить поля OAuth и таблицу webhook_events.

Revision ID: 0002
Revises: 0001_initial
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("instagram_accounts", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("instagram_accounts", sa.Column("ig_user_id", sa.String(64), nullable=True))
    op.add_column("instagram_accounts", sa.Column("page_id", sa.String(64), nullable=True))
    op.add_column("instagram_accounts", sa.Column("access_token_encrypted", sa.Text(), nullable=True))
    op.add_column("instagram_accounts", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f("ix_instagram_accounts_ig_user_id"), "instagram_accounts", ["ig_user_id"], unique=False)
    op.create_unique_constraint("uq_instagram_accounts_ig_user_id", "instagram_accounts", ["ig_user_id"])

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_events_event_id"), "webhook_events", ["event_id"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_webhook_events_event_id"), table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_constraint("uq_instagram_accounts_ig_user_id", "instagram_accounts", type_="unique")
    op.drop_index(op.f("ix_instagram_accounts_ig_user_id"), table_name="instagram_accounts")
    op.drop_column("instagram_accounts", "token_expires_at")
    op.drop_column("instagram_accounts", "access_token_encrypted")
    op.drop_column("instagram_accounts", "page_id")
    op.drop_column("instagram_accounts", "ig_user_id")
    op.drop_column("instagram_accounts", "updated_at")
