"""Per-giver promise numbering + backfill + composite unique constraint.

Revision ID: c4d8f1e2a3b5
Revises: b3d9e2f1a8c7
Create Date: 2026-08-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "c4d8f1e2a3b5"
down_revision = "b3d9e2f1a8c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Drop existing unique constraint on promise_id (if it exists)
    with op.batch_alter_table("promises", schema=None) as batch_op:
        try:
            batch_op.drop_constraint("uq_promises_promise_id", type_="unique")
        except Exception:
            pass  # Constraint may not exist in all DB states

    # Step 2: Backfill promise_id per-giver (starting from 1 for each giver)
    # Use raw SQL for this since it involves window functions
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE promises
            SET promise_id = (
                SELECT COUNT(*)
                FROM promises AS p2
                WHERE p2.giver_id = promises.giver_id
                  AND p2.created_at <= promises.created_at
            )
            WHERE promise_id IS NOT NULL OR promise_id IS NULL
        """)
    )

    # Step 3: Add composite unique constraint
    with op.batch_alter_table("promises", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_giver_promise_id", ["giver_id", "promise_id"]
        )


def downgrade() -> None:
    # Drop composite unique constraint
    with op.batch_alter_table("promises", schema=None) as batch_op:
        batch_op.drop_constraint("uq_giver_promise_id", type_="unique")

    # Restore global sequential numbering
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE promises
            SET promise_id = (
                SELECT COUNT(*)
                FROM promises AS p2
                WHERE p2.created_at <= promises.created_at
            )
        """)
    )

    # Re-add original unique constraint
    with op.batch_alter_table("promises", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_promises_promise_id", ["promise_id"]
        )
