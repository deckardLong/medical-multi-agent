from langchain.agents import create_agent
from .llm import get_llm
from .prompts.system import SYSTEM_PROMPT
from .tools.calendar_tool import list_upcoming_events, propose_calendar_event
from .tools.medical_retrieval_tool import medical_retrieval_tool
from .tools.member_profile_tool import get_member_profile, propose_medical_record
from .tools.vision_extract_tool import vision_extract_tool
from .tools.web_search_tool import web_search_tool


TOOLS = [medical_retrieval_tool, web_search_tool, get_member_profile, propose_medical_record,
         list_upcoming_events, propose_calendar_event, vision_extract_tool]

agent = create_agent(get_llm(), tools=TOOLS, system_prompt=SYSTEM_PROMPT)