from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from .tools import tools
from .prompts import prompt
import os

api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model="gpt-3.5-turbo", 
    temperature=0,
    api_key=api_key,
    base_url="https://api.openai.com/v1",
    timeout=30,
    max_retries=2
)

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)