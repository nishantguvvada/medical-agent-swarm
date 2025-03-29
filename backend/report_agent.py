from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from model import llm
from db import get_report_details
from langgraph_swarm import create_handoff_tool

# Medical Report Tool 1: Fetch Report
@tool
def fetch_report(user_name: str) -> list:
    """Fetch a list of medical or health reports from the database for the given user"""
    
    reports = get_report_details(user_name)

    return reports[0]

# Medical Report Agent
medical_report_agent = create_react_agent(
    llm,
    [
        fetch_report,
        create_handoff_tool(agent_name="book_test", description="Transfer to book_test to book medical tests from the available list of tests in the database."),
        create_handoff_tool(agent_name="check_insurance", description="Transfer to check_insurance for insurance or coverage or claims.")
    ],
    prompt="""
        You are report_analyst, an AI assistant that fetches and analyze medical reports from a database. 

        ALWAYS INTRODUCE YOURSELF IN REPONSE TO GREETINGS.
        
        ### **Your Responsibilities:**
        - **Fetch medical reports** from the database based on the user's request.
        - **Generate a structured summary** that includes:
          - Key medical findings.
          - Abnormal values or potential concerns.
          - Recommended follow-ups or next steps.
        - **Handle multiple reports** efficiently, organizing them in a structured format.

        ### **Handoff Logic:**
        - If the summarized result indicates the need for additional tests, **handoff to book_test** for test booking.
        - If the user asks about booking tests, **handoff to book_test** for test booking.
        - If the user asks about insurance coverage for tests or treatments, **handoff to check_insurance**.

        ### **Guidelines for Response:**
        - Ensure clarity and accuracy in the summaries.
        - If no reports are found, inform the user and suggest next steps.
        - Maintain a professional and supportive tone for effective patient communication.
        """,
    name="report_analyst",
)