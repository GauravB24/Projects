from fastapi import FastAPI

from app.agent import Agent
from app.models import AgentRequest

app = FastAPI(
    title="Autonomous AI Agent",
    version="1.0.0",
    description="AI Agent Assignment"
)

agent = Agent()


@app.get("/")
def home():
    return {
        "status": "Running",
        "message": "Autonomous AI Agent API is running successfully."
    }


@app.post("/agent")
def run_agent(request: AgentRequest):

    return agent.process_request(request.request)