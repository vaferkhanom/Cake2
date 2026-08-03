import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_PATH = "/data/promise-bot/test_promise_bot.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

async def migrate():
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # 1. Add promise_id column (human-friendly sequential ID)
        try:
            await conn.execute(text("ALTER TABLE promises ADD COLUMN promise_id INTEGER;"))
            print("Added promise_id column")
        except Exception as e:
            print(f"promise_id column might already exist: {e}")
        
        # 2. Backfill promise_id with sequential numbers based on existing id
        await conn.execute(text("UPDATE promises SET promise_id = id;"))
        print("Backfilled promise_id")
        
        # 3. Make promise_id NOT NULL and UNIQUE
        try:
            await conn.execute(text("CREATE UNIQUE INDEX idx_promises_promise_id ON promises(promise_id);"))
            print("Created unique index on promise_id")
        except Exception as e:
            print(f"Unique index might already exist: {e}")
        
        print("Migration completed successfully!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())