from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from insurance_agent import insurance_agent
from report_agent import medical_report_agent
from test_booking_agent import test_booking_agent
from langgraph_swarm import create_swarm

checkpointer = InMemorySaver() # checkpointer.list(config) store in MongoDB
store = InMemoryStore()

workflow = create_swarm(
    [medical_report_agent, test_booking_agent, insurance_agent],
    default_active_agent="report_analyst"
)

swarm = workflow.compile(
    checkpointer=checkpointer,
    store=store
)