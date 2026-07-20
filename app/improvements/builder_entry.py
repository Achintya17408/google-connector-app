import asyncio

from app.db.connection import close_pool, get_pool
from app.improvements.builder import candidate_builder_loop


async def main():
    stop = asyncio.Event()
    try:
        await candidate_builder_loop(await get_pool(), stop)
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
