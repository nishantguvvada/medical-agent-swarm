from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

def get_database():

    client = MongoClient(os.getenv('MONGODB_URL'))

    return client[os.getenv('DB')]