from uuid import UUID
from langchain_core.runnables import RunnableConfig

def member_id_from(config: RunnableConfig) -> UUID:
    """Get member ID from config, not LLM since if someone can use LLM to read ID from other users"""
    try:
        return UUID(config["configurable"]["member_id"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Thiếu member_id trong config - Tool chỉ được gọi qua chat service") 