import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import fetch_all, close_pool

async def test():
    r = await fetch_all('SELECT * FROM teams')
    print('Teams:', [dict(x) for x in r])
    r2 = await fetch_all('SELECT * FROM team_members')
    print('Team Members:', [dict(x) for x in r2])
    print("DONE")
    await close_pool()

if __name__ == "__main__":
    asyncio.run(test())
