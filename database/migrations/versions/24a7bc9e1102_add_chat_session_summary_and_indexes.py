"""add_chat_session_summary_and_indexes

Revision ID: 24a7bc9e1102
Revises: 13f855e98e64
Create Date: 2026-10-31 12:18:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '24a7bc9e1102'
down_revision: Union[str, None] = '13f855e98e64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('summary', sa.Text(), nullable=True))
        batch_op.create_index('ix_chat_sessions_user_updated', ['user_id', 'updated_at'], unique=False)
        batch_op.create_index('ix_chat_sessions_user_deleted_updated', ['user_id', 'is_deleted', 'updated_at'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('chat_sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_chat_sessions_user_deleted_updated')
        batch_op.drop_index('ix_chat_sessions_user_updated')
        batch_op.drop_column('summary')
