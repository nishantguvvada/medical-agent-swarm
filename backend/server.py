from fastapi import FastAPI
from pydantic import BaseModel
from typing_extensions import Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from swarm import swarm
from dotenv import load_dotenv
from db import get_thread_from_db, save_thread_to_db, save_chat_logs
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

    # If user_thread_id is provided in the request body, fetch the context from the database
    if user_thread_id:
        fetched_context = get_thread_from_db(user_thread_id)
        stored_context = {"messages": fetched_context["messages"], "metadata": fetched_context["metadata"], "usage": fetched_context["usage"]}
        thread_id = user_thread_id
    else:
        thread_id = str(uuid.uuid4())  # Create a new thread
        stored_context = {"messages": [], "metadata": [], "usage": []}  # Start with an empty conversation

    # Assign the MongoDB checkpointer so the swarm uses it for state tracking
    config = {"configurable": {"thread_id": f"{thread_id}"}}

    # Run the agent swarm (this generates a new checkpoint)
    response = swarm.invoke({"messages": [{"role": "user", "content": user_query}]}, config=config, stream_mode="values")

    stored_context["messages"].append(response["messages"][-1].content)
    stored_context["usage"].append(response["messages"][-1].usage_metadata)
    stored_context["metadata"].append(response["messages"][-1].response_metadata)

    save_thread_to_db(thread_id, stored_context)

    # Fetch the latest checkpoint directly from the swarm
    new_checkpoint = swarm.checkpointer.get(config)

    save_chat_logs(thread_id, new_checkpoint)

    return {"thread_id": thread_id, "response": response["messages"][-1].content, "checkpoint": new_checkpoint}

if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)