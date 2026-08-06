"""Phase 5: Add score/streak to User, update PromiseStatus enum, add deadline/claim fields

Revision ID: a75af508a777
Revises: afcb6cc74ab8
Create Date: 2026-08-04 10:06:01.943139
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a75af508a777'
down_revision: Union[str, Sequence[str], None] = 'afcb6cc74ab8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — dialect-aware (SQLite needs batch rebuild, Postgres direct DDL)."""
    op.add_column('users', sa.Column('score', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('current_streak', sa.Integer(), nullable=False, server_default='0'))
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('full_name',
                                  existing_type=sa.VARCHAR(length=255),
                                  type_=sa.String(length=512),
                                  existing_nullable=False)
    else:
        op.alter_column('users', 'full_name',
                        existing_type=sa.VARCHAR(length=255),
                        type_=sa.String(length=512),
                        existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('users') as batch_op:
            batch_op.alter_column('full_name',
                                  existing_type=sa.String(length=512),
                                  type_=sa.VARCHAR(length=255),
                                  existing_nullable=False)
    else:
        op.alter_column('users', 'full_name',
                        existing_type=sa.String(length=512),
                        type_=sa.VARCHAR(length=255),
                        existing_nullable=False)
    op.drop_column('users', 'current_streak')
    op.drop_column('users', 'score')
