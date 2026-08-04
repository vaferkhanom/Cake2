"""Phase 6: Add giver_pending_message_id and giver_pending_chat_id

Revision ID: b3d9e2f1a8c7
Revises: a75af508a777
Create Date: 2026-08-04 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3d9e2f1a8c7'
down_revision: Union[str, Sequence[str], None] = 'a75af508a777'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add pending message fields for accept/reject edit flow."""
    with op.batch_alter_table('promises', schema=None) as batch_op:
        batch_op.add_column(sa.Column('giver_pending_message_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('giver_pending_chat_id', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('promises', schema=None) as batch_op:
        batch_op.drop_column('giver_pending_chat_id')
        batch_op.drop_column('giver_pending_message_id')
