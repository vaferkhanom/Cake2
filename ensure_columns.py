#!/usr/bin/env python3
"""Add missing columns to promises table on Postgres if they don't exist."""
import asyncpg
import os
import asyncio

async def ensure_columns():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    
    # Check existing columns
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'promises'")
    existing = {r["column_name"] for r in rows}
    
    # Add missing columns
    missing = []
    if "deadline" not in existing:
        missing.append(("deadline", "ALTER TABLE promises ADD COLUMN deadline TIMESTAMP WITH TIME ZONE"))
    if "claimed_done_at" not in existing:
        missing.append(("claimed_done_at", "ALTER TABLE promises ADD COLUMN claimed_done_at TIMESTAMP WITH TIME ZONE"))
    if "resolved_at" not in existing:
        missing.append(("resolved_at", "ALTER TABLE promises ADD COLUMN resolved_at TIMESTAMP WITH TIME ZONE"))
    
    for name, sql in missing:
        print(f"Adding column: {name}")
        await conn.execute(sql)
    
    await conn.close()
    print("Done")

asyncio.run(ensure_columns())