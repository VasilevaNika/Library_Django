"""create all tables for reviews service

Revision ID: b3c4d5e6f7g8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-31 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Создаём таблицу library_users если её нет
    op.execute("""
        CREATE TABLE IF NOT EXISTS library_users (
            id INTEGER PRIMARY KEY
        )
    """)
    
    # Создаём таблицу reading_list_entries
    op.create_table(
        'reading_list_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('priority', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['library_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='uq_reading_user_book')
    )
    op.create_index('ix_reading_list_entries_user_id', 'reading_list_entries', ['user_id'])
    op.create_index('ix_reading_list_entries_book_id', 'reading_list_entries', ['book_id'])

def downgrade() -> None:
    op.drop_index('ix_reading_list_entries_book_id', table_name='reading_list_entries')
    op.drop_index('ix_reading_list_entries_user_id', table_name='reading_list_entries')
    op.drop_table('reading_list_entries')
    op.execute("DROP TABLE IF EXISTS library_users")