from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from product.config import ProductEnv

env = ProductEnv()

# Get DB session
engine = create_async_engine(env.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    """Dependency for Fast API"""
    async with SessionLocal() as session:
        yield session