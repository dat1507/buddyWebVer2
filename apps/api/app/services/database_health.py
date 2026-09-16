"""Database health probe service."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database(session: AsyncSession) -> bool:
    """Execute the smallest useful database round trip."""
    result = await session.execute(text("SELECT 1"))
    return bool(result.scalar_one() == 1)
