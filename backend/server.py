from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from agent import invoke_agent
import os

load_dotenv()

app = FastAPI()

origins = [
    # f"{os.getenv('FRONTEND_URL')}"
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def default():
    return {"response":"on"}

class UserInput(BaseModel):
    user_query: str

@app.post("/ask")
def invoke_llm(user_input: UserInput):
    # llm call
    response = invoke_agent(user_input.user_query)
    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)