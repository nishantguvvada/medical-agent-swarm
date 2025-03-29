from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

def get_database():

    client = MongoClient(os.getenv('MONGODB_URL'))

    return client[os.getenv('DB')]

db = get_database()
thread_collection = db[os.getenv('THREAD_COLLECTION')]
test_collection = db[os.getenv('TEST_COLLECTION')]
report_collection = db[os.getenv('REPORT_COLLECTION')]
treatment_collection = db[os.getenv('TREATMENT_COLLECTION')]
insurance_collection = db[os.getenv('INSURANCE_COLLECTION')]
user_collection = db[os.getenv('USER_COLLECTION')]
logs_collection = db[os.getenv('LOG_COLLECTION')]

def get_user_details(user_name: str):

    user_details = user_collection.find({"user_name": user_name.lower()})

    return user_details

def get_insurance_policy_details_from_user_id(user_id):

    policy = insurance_collection.find_one({"patient_id": user_id})

    return policy

def get_insurance_policy_details_from_policy(policy_number):

    policy = insurance_collection.find_one({"policy_number": policy_number})

    return policy

def get_treatment_details(treatment: str):

    treatment_details = treatment_collection.find({"test_name": treatment})

    return treatment_details

def get_report_details(user_name: str):

    user_details = get_user_details(user_name)

    report_details = report_collection.find({"user_id": user_details[0]["_id"]})

    return report_details

def get_booked_test_details(user_name: str):

    user_details = get_user_details(user_name)

    test_details = test_collection.find({"patient_id": user_details[0]["_id"]})

    return test_details

def get_available_tests():

    test_details = treatment_collection.find({})

    return test_details

def get_thread_from_db(thread_id):
    """Retrieve thread from MongoDB"""

    thread = thread_collection.find_one({"thread_id": thread_id})

    return thread if thread else None

def save_thread_to_db(thread_id, stored_context):
    """Save thread to MongoDB"""

    response = thread_collection.update_one(
        {"thread_id": thread_id}, 
        {"$set": {"messages": stored_context["messages"], "usage": stored_context["usage"], "metadata": stored_context["metadata"]}}, 
        upsert=True
    )

    return response

def save_chat_logs(thread_id, checkpoint):
    """Save chat logs to MongoDB"""

    messages = [
        {
            "type": message.type, 
            "name": message.name, 
            "content": message.content,
        } for message in checkpoint["channel_values"]["messages"]
    ]

    response = logs_collection.update_one(
        {"thread_id": thread_id},
        {"$set":{"checkpoint": messages}},
        upsert=True
    )

    return response
