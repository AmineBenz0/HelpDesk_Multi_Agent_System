import time
import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing_extensions import TypedDict

from celery import Celery
from celery.result import AsyncResult

from langgraph.graph import StateGraph, START, END

import requests
from celery.signals import task_success


from langgraph.graph import StateGraph
from src.core.email_service import EmailService
from src.core.gmail_service import GmailService
from src.core.outlook_service import OutlookService
from src.core.llm_handler import LLMHandler
from src.core.ticket_management import TicketManager
from src.core.workflow import create_workflow
from src.monitoring.gmail_monitor import GmailMonitor
from src.monitoring.outlook_monitor import OutlookMonitor
from src.utils.logger import logger
from src.agents.classification_agent import ClassifierAgent
from src.agents.demande_agent import DemandeAgent
from src.agents.field_extraction_agent import FieldExtractionAgent
from src.agents.missing_fields_follow_up_agent import MissingFieldsFollowUpAgent
from src.agents.user_response_monitor import UserResponseMonitor
from src.agents.subcategory_extraction_agent import SubcategoryExtractionAgent
from src.agents.priority_detection_agent import PriorityDetectionAgent
from src.agents.ticket_creation_agent import TicketCreationAgent
from src.agents.confirm_subcategory_follow_up_agent import ConfirmSubcategoryFollowUpAgent
from src.agents.subcategory_response_monitor import SubcategoryResponseMonitor
from src.agents.missing_subcategory_follow_up_agent import MissingSubcategoryFollowUpAgent
from src.agents.priority_follow_up_agent import PriorityFollowUpAgent
from src.agents.priority_response_monitor import PriorityResponseMonitor

from src.core.workflow import create_workflow
from src.core.workflow import EmailState

app = FastAPI()

class MyGraphState(TypedDict):
    count: int
    msg: str

def counter(state: MyGraphState):
    state["count"] += 1
    state["msg"] = f"Called {state['count']} time(s)"
    time.sleep(20)  
    return state

def build_graph():
    wf = StateGraph(MyGraphState)
    wf.add_node("Node1", counter)
    wf.add_node("Node2", counter)
    wf.add_node("Node3", counter)
    wf.add_edge(START, "Node1")
    wf.add_edge("Node1", "Node2")
    wf.add_edge("Node2", "Node3")
    wf.add_edge("Node3", END)
    return wf.compile()



email_service = GmailService()
llm_handler = LLMHandler()
ticket_manager = TicketManager()

# Initialize Agents with provider-agnostic email_service
classifier_agent = ClassifierAgent(llm_handler)
demande_agent = DemandeAgent(email_service)
field_extraction_agent = FieldExtractionAgent(llm_handler, email_service, ticket_manager)
missing_fields_follow_up_agent = MissingFieldsFollowUpAgent(email_service, llm_handler)
user_response_monitor = UserResponseMonitor(email_service, llm_handler)
subcategory_extraction_agent = SubcategoryExtractionAgent(llm_handler, ticket_manager)    
priority_detection_agent = PriorityDetectionAgent(llm_handler, ticket_manager)
ticket_creation_agent = TicketCreationAgent(ticket_manager)
confirm_subcategory_follow_up_agent = ConfirmSubcategoryFollowUpAgent(email_service, llm_handler)
subcategory_response_monitor = SubcategoryResponseMonitor(email_service, llm_handler)
missing_subcategory_follow_up_agent = MissingSubcategoryFollowUpAgent(email_service, llm_handler)
priority_follow_up_agent = PriorityFollowUpAgent(email_service, llm_handler)
priority_response_monitor = PriorityResponseMonitor(email_service, llm_handler)

# graph = build_graph()
graph = create_workflow(
        classifier_agent=classifier_agent,
        demande_agent=demande_agent,
        field_extraction_agent=field_extraction_agent,
        subcategory_extraction_agent=subcategory_extraction_agent,
        priority_detection_agent=priority_detection_agent,
        ticket_creation_agent=ticket_creation_agent,
        missing_fields_follow_up_agent=missing_fields_follow_up_agent,
        user_response_monitor=user_response_monitor,
        confirm_subcategory_follow_up_agent=confirm_subcategory_follow_up_agent,
        subcategory_response_monitor=subcategory_response_monitor,
        missing_subcategory_follow_up_agent=missing_subcategory_follow_up_agent,
        priority_follow_up_agent=priority_follow_up_agent,
        priority_response_monitor=priority_response_monitor
    )

# ——— 2) Celery setup ———
celery_app = Celery(
    "helpdesk",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    worker_concurrency=4,
)

@celery_app.task(name="invoke_graph")
def invoke_graph(payload: dict):
    # return graph.invoke(payload)
    return graph.process_message(payload)



# class Payload(BaseModel):
#     count: int
#     msg: str

class EmailPayload(BaseModel):
    email_data: dict

@app.post("/process_email")
# def process_email(email: Payload):
def process_email(email: EmailPayload):
    payload = EmailState(email_data=email.email_data)
    task = invoke_graph.delay(payload)
    # task = invoke_graph(payload)
    return {"status": "queued", "task_id": task.id}
    # return task

@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result
    }



WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://wh_app:8001/my-webhook")

@task_success.connect(sender="invoke_graph")
def on_task_success(sender=None, result=None, **kwargs):
    try:
        requests.post(
            WEBHOOK_URL,
            json={
                "task_id": kwargs.get("task_id"),
                "status": "SUCCESS",
                "result": result,
            },
            timeout=5
        ).raise_for_status()
    except Exception as e:
        print(f"⚠️ Webhook notification failed: {e}")