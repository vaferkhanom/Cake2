"""Phase 3/4: Add deadline, claimed_done_at, resolved_at, giver_claim_message_id, giver_claim_chat_id

Revision ID: 9d8e7f6a5b4c
Revises: afcb6cc74ab8
Create Date: 2026-08-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '9d8e7f6a5b4c'
down_revision: Union[str, Sequence[str], None] = 'afcb6cc74ab8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add deadline, claimed_done_at, resolved_at, claim fields."""
    bind = op.get_bind()
    # Add deadline, claimed_done_at, resolved_at
    op.add_column('promises', sa.Column('deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('promises', sa.Column('claimed_done_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('promises', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    # giver_claim_message_id and giver_claim_chat_id already added by afcb6cc74ab8


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.drop_column('promises', 'resolved_at')
    op.drop_column('promises', 'claimed_done_at')
    op.drop_column('promises', 'deadline')
    # Don't drop claim fields - handled by afcb6cc74ab8