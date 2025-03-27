from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()


llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', api_key=os.getenv('GEMINI_API_KEY'))

tools = [] 

agent = create_react_agent(
    llm,
    tools,
    state_modifier=(
        "You are a medical assistant. You analyze all the documents provided by the user and generate a report for the medical expert."
        "You MUST always be polite and happy while responding to the user."
        "You MUST only respond precisely in 100 words."
    )
)

def invoke_agent(user_input):
    response = agent.invoke({"messages": [("human", user_input)]})
    return response["messages"][-1].content