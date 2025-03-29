from fastapi import FastAPI
from pydantic import BaseModel
from typing_extensions import Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from swarm import swarm
from dotenv import load_dotenv
from db import get_thread_from_db, save_thread_to_db
import uuid
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
    thread_id: Optional[str] = None

@app.post("/ask")
async def invoke_llm(user_input: UserInput):
    user_query = user_input.user_query
    user_thread_id = user_input.thread_id

    if user_thread_id:
        stored_context = await get_thread_from_db(user_thread_id)
        thread_id = user_thread_id
    else:
        thread_id = str(uuid.uuid4())  # Create a new thread
        stored_context = {"messages": [], "metadata": []}  # Start with an empty conversation

    response = swarm.invoke({"messages": [{"role": "user", "content": user_query}]}, config={"configurable": {"thread_id": f"{thread_id}"}}, stream_mode="values")

    stored_context["messages"].append(response["messages"][-1].content)
    stored_context["usage"].append(response["messages"][-1].usage_metadata)
    stored_context["metadata"].append(response["messages"][-1].response_metadata)

    save_thread_to_db(thread_id, stored_context)

    return {"thread_id": thread_id, "response": response["messages"][-1].content}

if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)