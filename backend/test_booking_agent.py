from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from model import llm
from db import get_user_details, get_available_tests, get_database
from langgraph_swarm import create_handoff_tool
import random
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Medical Test Booking Tool 1: Book Tests
@tool
def book_tests(user_name: str): 
    # https://www.googlecloudcommunity.com/gc/AI-ML/Gemini-API-400-Bad-Request-Array-fields-breaks-function-calling/m-p/770472#M7974
    # Trying to pass array input from one tool to another gives error. Work on it later.
    # ChatGoogleGenerativeAIError: Invalid argument provided to Gemini: 400 * GenerateContentRequest.tools[0].function_declarations[1].parameters.properties[fetched_tests].items: missing field.
    """Create a booking appointment and store it in the database."""

    user_details = get_user_details(user_name)

    tests = get_available_tests()
    fetched_tests = list(tests)

    tests = random.choices(fetched_tests, k=random.randint(1, 4))
    all_tests = [test["test_name"] for test in tests]
    total_cost = sum([test["cost"] for test in tests])

    booking_details = {
        "patient_id": user_details[0]['_id'],
        # "lab_name": lab_name,
        "test_name": all_tests,
        "total_cost": total_cost,
        "date_time": f"{datetime.datetime.now()}",
        "status": "Confirmed"
    }

    db = get_database()

    test_collection = db[os.getenv('TEST_COLLECTION')]

    test_details = test_collection.insert_one(booking_details)

    return test_details.inserted_id

# Medical Test Booking Tool 2: Fetch Tests    
@tool
def fetch_tests() -> list:
    """Fetch all the available tests from the database and returns the list of tests"""
    
    available_tests = get_available_tests()
    fetched_tests = list(available_tests)

    return fetched_tests

# Medical Test Booking Agent
test_booking_agent = create_react_agent(
    llm,
    [
        fetch_tests, 
        book_tests, 
        create_handoff_tool(agent_name="report_analyst", description="Transfer to report_analyst for analysis of user's medical reports."),
        create_handoff_tool(agent_name="check_insurance", description="Transfer to check_insurance for insurance or coverage or claims.")
    ],
    prompt="""
        You are book_test, an AI-powered medical test booking assistant.

        Your role is to book medical tests from the available list of tests in the database.
        
        ### **Your Responsibilities:**
        - **Fetch available medical tests** from the database before proceeding with any booking.
        - **Book tests** requested by the user from the available options.
        - **Provide pre-test instructions** (e.g., fasting requirements, special preparations) for each test.
        - **Ensure a structured, clear, and medically relevant response** to assist in patient care.

        ### **Booking Guidelines:**
        - ALWAYS **share the booking ID** with the user upon successful booking.
        - After booking, ALWAYS **ask the user about insurance** and, if needed, hand off to the `check_insurance` agent.
        - If a medical report needs further analysis, hand off to the `report_analyst` agent.

        ### **Important Notes:**
        - If the requested test is not available, inform the user and suggest alternative tests if possible.
        - Maintain a professional, helpful, and concise tone in your responses.
    """, # Given symptoms or a specific test request, you find the best match and book an appointment. 
    name="book_test",
)
