#!/usr/bin/env python3
import asyncpg
import os
import asyncio

async def check():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'promises' ORDER BY ordinal_position")
    await conn.close()
    print("Columns:", [r["column_name"] for r in rows])

asyncio.run(check())