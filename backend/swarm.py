from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_swarm import create_handoff_tool, create_swarm
import datetime
import random
from dotenv import load_dotenv
from db import get_database, get_user_details, get_insurance_policy_details, get_treatment_details, get_report_details, get_booked_test_details, get_available_tests
import os

load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', api_key=os.getenv('GEMINI_API_KEY'))

# Insurance Tool 1: Fetch Insurance Details
@tool
def fetch_insurance_policy_details(user_name: str) -> dict:
    """Fetches the user's insurance policy details from the database."""

    user_details = get_user_details(user_name)

    policy = get_insurance_policy_details(user_details[0]["_id"])

    return policy if policy else {"error": "No insurance policy found for this patient."}

# Insurance Tool 2: Check Insurance Claim Eligibility
@tool
def check_claim_eligibility(policy: dict, treatment: str) -> str:
    """Checks if a treatment is covered under the user's insurance policy ensuring user is eligible for insurance claim."""

    covered_treatments = policy.get("covered_treatments", [])
    
    if treatment in covered_treatments:
        return f"Treatment '{treatment}' is covered by insurance."
    else:
        return f"Treatment '{treatment}' is NOT covered under the current insurance plan."
    
# Insurance Tool 3: Calculate Estimated Coverage
@tool
def calculate_estimated_coverage(policy: dict, treatment: str) -> dict:
    """Calculates the insurance coverage percentage and estimated amount reimbursed."""

    treatment_details = get_treatment_details(treatment)

    coverage_percentage = policy.get("coverage_percentage", 0)  # Default 0% if not found
    reimbursed_amount = (coverage_percentage / 100) * treatment_details[0]["cost"]

    return { 
        "coverage_percentage": coverage_percentage, 
        "treatment": treatment, 
        "estimated_reimbursement": reimbursed_amount, 
        "total_cost": treatment_details[0]["cost"] 
    }

# Insurance Tool 4: Submit Claim 
@tool
def submit_insurance_claim(user_name: str ,coverage_percentage: float, treatment: str, estimated_reimbursement: float, total_cost: float) -> str:
    """Submits an insurance claim for approval."""

    user_details = get_user_details(user_name)

    coverage_details = { 
        "coverage_percentage": coverage_percentage, 
        "treatment": treatment, 
        "estimated_reimbursement": estimated_reimbursement, 
        "total_cost": total_cost
    }

    # Simulate claim submission
    claim_id = f"CLAIM-{user_details[0]["_id"]}-{hash(treatment)}"
    return f"Claim Submitted! ID: {claim_id}\n{coverage_details}"

# Insurance Agent
insurance_agent = create_react_agent(
    llm,
    [
        fetch_insurance_policy_details, 
        check_claim_eligibility, 
        calculate_estimated_coverage,
        submit_insurance_claim,
        # create_handoff_tool(agent_name="Payme", description="Transfer to Payme for payments.")
    ],
    prompt="""
        You are CheckInsurance, an AI-powered insurance assistant specialized in handling medical insurance queries. 
        Your primary tasks include retrieving insurance policy details, checking claim eligibility based on user-provided information, 
        calculating estimated coverage for treatments, and submitting insurance claims. 
        Given the patient's details and required treatment, efficiently guide them through the insurance process while ensuring accuracy and compliance. 
        Always provide clear and actionable responses.
        For any topic related to payments, transfer to Payme.
        """,
    name="CheckInsurance",
)

# Medical Report Tool 1: Fetch Report
@tool
def fetch_report(user_name: str) -> list:
    """Fetch a list of medical or health reports from the database for the given user"""
    
    reports = get_report_details(user_name)

    return reports[0]

# Medical Report Agent
medical_report_agent = create_react_agent(
    llm,
    [fetch_report, create_handoff_tool(agent_name="TestRecommender", description="Transfer to TestRecommender to recommend tests.")],
    prompt="""
        You are ReportAnalyst, an AI assistant that fetches and analyze medical reports from a database. 
        After fetching the reports, you generate a concise summary highlighting key medical findings, abnormal values, and any suggested action. 
        If the patient has multiple reports, return all of them in a structured format. 
        """,
    name="ReportAnalyst",
)

# Medical Test Booking Tool 1: Book Tests
@tool
def book_tests(user_name: str): 
    # https://www.googlecloudcommunity.com/gc/AI-ML/Gemini-API-400-Bad-Request-Array-fields-breaks-function-calling/m-p/770472#M7974
    # Trying to pass array input from one tool to another gives error. Work on it later.
    # ChatGoogleGenerativeAIError: Invalid argument provided to Gemini: 400 * GenerateContentRequest.tools[0].function_declarations[1].parameters.properties[fetched_tests].items: missing field.
    """Create a booking appointment and store it in the database.
    """

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
    [fetch_tests, book_tests, create_handoff_tool(agent_name="CheckInsurance", description="Transfer to CheckInsurance for anything related to insurance or coverage or claims.")],
    prompt="""
        You are BookTest, an AI-powered medical test booking assistant. 
        Your role is to book medical tests from the available list of tests in the database.
        Fetch all the available tests from the database before booking the tests.
        You also provide pre-test instructions (e.g., fasting, special preparations). 
        Your responses should be clear, structured, and medically relevant for efficient patient care.
    """, # Given symptoms or a specific test request, you find the best match and book an appointment. 
    name="BookTest",
)

# Medical Test Recommendation Agent
test_recommendation_agent = create_react_agent(
    llm,
    [create_handoff_tool(agent_name="BookTest", description="Transfer to BookTest for booking medical tests.")],
    prompt="""
        You are TestRecommender, an AI-powered medical test recommendation assistant. 
        Recommend the medical tests from the below list of tests based on user's medical issues. 
        Your responses should be medically accurate and concise.
        Use the below list of symptom to test mapping to build your recommendations.
        [
            { "symptom": "headache", "tests": ["CT Scan", "MRI Scan"] },
            { "symptom": "fever", "tests": ["Blood Report"] },
            { "symptom": "thyroid issues", "tests": ["Thyroid Function Test"] },
            { "symptom": "chest pain", "tests": ["ECG", "Cardiac Stress Test"] },
            { "symptom": "breathing issues", "tests": ["Pulmonary Function Test", "Chest X-Ray"] },
            { "symptom": "fatigue", "tests": ["Complete Blood Count", "Thyroid Function Test"] },
            { "symptom": "joint pain", "tests": ["Rheumatoid Factor Test", "X-Ray"] },
            { "symptom": "dizziness", "tests": ["Blood Pressure Test", "ECG"] },
            { "symptom": "stomach pain", "tests": ["Abdominal Ultrasound", "Liver Function Test"] },
            { "symptom": "weight loss", "tests": ["Diabetes Test", "Hormone Panel"] }
        ]
    """,
    name="TestRecommender",
)

# @tool
# def extracted_user_data(user_name: str, medical_issue: str):
#     """Extract the user name and medical issue from the user query"""
#     return {user_name: user_name, medical_issue: medical_issue}


# Main Agent
consult_agent = create_react_agent(
    llm,
    [
        # extracted_user_data,
        create_handoff_tool(agent_name="ReportAnalyst", description="Transfer to ReportAnalyst for fetching user's medical history."),
        create_handoff_tool(agent_name="TestRecommender", description="Transfer to TestRecommender for recommending medical tests."),
        create_handoff_tool(agent_name="CheckInsurance", description="Transfer to CheckInsurance for anything related to insurance or coverage or claims."),
        create_handoff_tool(agent_name="BookTest", description="Transfer to BookTest for booking medical tests."),
    ],
    prompt="""
        You are MedicalConsultant, an AI-powered medical consultant. 
        Your role is to provide medical recommendations to the user's health related queries.
        
        Always analyze user's medical history, followed by recommending tests.
        You DO NOT answer anything unrelated to health or the medical domain. 
        Your responses should be clear, structured, and medically relevant for efficient patient care.
    """, # Extract the user name from the user query or ask for it if not provided.
    name="MedicalConsultant",
)
checkpointer = InMemorySaver() # checkpointer.list(config) store in MongoDB
store = InMemoryStore()

workflow = create_swarm(
    [consult_agent, medical_report_agent, test_recommendation_agent, test_booking_agent, insurance_agent],
    default_active_agent="BookTest"
)
app = workflow.compile(
    checkpointer=checkpointer,
    store=store
    )

config = {"configurable": {"thread_id": "2"}}

# def stream_graph_updates(user_input: str):
#     for event in app.stream({"messages": [{"role": "user", "content": user_input}]}, config=config):
#         for value in event.values():
#             print("Assistant:", value["messages"][-1].content)

# while True:
#     user_input = input("User: ")
#     if user_input.lower() in ["quit", "exit", "q"]:
#         print("Exit")
#         break
#     stream_graph_updates(user_input)


turn_1 = app.invoke(
    {"messages": [{"role": "user", "content": "book a ct scan for jannet."}]},
    config,
)

print(turn_1)

# turn_2 = app.invoke(
#     {"messages": [{"role": "user", "content": "what is the health summary of Jannet?"}]},
#     config,
# )
# print(turn_2)



