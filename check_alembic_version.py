#!/usr/bin/env python3
import asyncpg
import os
import asyncio

async def check():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    row = await conn.fetchrow("SELECT version_num FROM alembic_version")
    await conn.close()
    print("Current alembic version:", row["version_num"] if row else "none")

asyncio.run(check())