"""init — таблица notifications

Revision ID: b4989785393f
Revises:
Create Date: 2026-03-21 02:26:43.959544

"""
from alembic import op
import sqlalchemy as sa


revision = "b4989785393f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Если раньше применялась версия с tasks — убираем её
    op.execute("DROP TABLE IF EXISTS tasks CASCADE")
    op.execute('DROP INDEX IF EXISTS ix_tasks_id')

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("message", sa.String(length=4096), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "priority",
            sa.String(length=16),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("related_data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(
        op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")
