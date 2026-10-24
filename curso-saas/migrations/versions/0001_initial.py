"""Первые таблицы: users, instagram_accounts, automations

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "instagram_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "username", name="uq_instagram_accounts_user_username"),
    )
    op.create_index(op.f("ix_instagram_accounts_user_id"), "instagram_accounts", ["user_id"], unique=False)

    op.create_table(
        "automations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("instagram_account_id", sa.Integer(), nullable=True),
        sa.Column("keyword", sa.String(length=100), nullable=False),
        sa.Column("direct_message", sa.Text(), nullable=False),
        sa.Column("public_reply", sa.String(length=300), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instagram_account_id"], ["instagram_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automations_user_id"), "automations", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_automations_user_id"), table_name="automations")
    op.drop_table("automations")
    op.drop_index(op.f("ix_instagram_accounts_user_id"), table_name="instagram_accounts")
    op.drop_table("instagram_accounts")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
