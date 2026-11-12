from langchain_openai import ChatOpenAI
from product.config import ProductEnv

env = ProductEnv()

def get_llm():
    return ChatOpenAI(base_url=env.llm_base_url, api_key=env.llm_api_key, model=env.llm_model, temperature=0)