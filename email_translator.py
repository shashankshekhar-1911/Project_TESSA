#Extracts relevant context from a client's email

#Importing modules
import os
import json
import email_parser
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Define the state type
class EmailState(TypedDict):
    body: str
    querySummary: str | None
    queryDescription: str | None
    queryNature: str | None
    queryUrgency: str | None
    querySentiment: str | None

# Initialize the LLM
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# Define the prompts
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an AI assistant that summarizes client emails. Provide a one-line summary that captures the main request using an infinitive verb at the start."),
    ("human", "What would be a fair 1 line summary of the ask that captures what is requested by the client as per the following email - {body}")
])

nature_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant that categorizes client emails. Select ONLY ONE of the following options: Query, Bug Reporting, New Request, or Just FYI. Do 
     not include any other text in your response."""),
    ("human", "What's the nature of the following email received from the client? {body}")
])

urgency_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant that assesses email urgency. Select ONLY ONE of the following options: High, Medium, or Low.  Do 
     not include any other text in your response."""),
    ("human", "What's the urgency of the ask by the client as per the following email? {body}")
])

sentiment_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant that analyzes email sentiment. Select ONLY ONE of the following options: Extremely Positive, Positive, Neutral, Negative, or Extremely Negative.  Do 
     not include any other text in your response."""),
    ("human", "What's the sentiment of the tone used by the client as per the following email? {body}")
])

# Define the nodes
def summarize_email(state: EmailState) -> EmailState:
    """Generate a one-line summary of the email."""
    response = llm.invoke(summary_prompt.format_messages(body=state["body"]))
    state["querySummary"] = response.content
    return state

def determine_nature(state: EmailState) -> EmailState:
    """Determine the nature of the email."""
    response = llm.invoke(nature_prompt.format_messages(body=state["body"]))
    state["queryNature"] = response.content
    return state

def assess_urgency(state: EmailState) -> EmailState:
    """Assess the urgency of the email."""
    response = llm.invoke(urgency_prompt.format_messages(body=state["body"]))
    state["queryUrgency"] = response.content
    return state

def analyze_sentiment(state: EmailState) -> EmailState:
    """Analyze the sentiment of the email."""
    response = llm.invoke(sentiment_prompt.format_messages(body=state["body"]))
    state["querySentiment"] = response.content
    return state

def decode_client_email(email_metadata: dict) -> dict:
    """Process the email metadata and return the analyzed context."""
    # Initialize the state
    initial_state: EmailState = {
        "body": email_metadata.get("body", ""),
        "querySummary": None,
        "queryDescription": email_metadata.get("body", ""),  # Using body as description
        "queryNature": None,
        "queryUrgency": None,
        "querySentiment": None
    }
    
    # Create the workflow
    workflow = StateGraph(EmailState)
    
    # Add nodes
    workflow.add_node("summarize", summarize_email)
    workflow.add_node("nature", determine_nature)
    workflow.add_node("urgency", assess_urgency)
    workflow.add_node("sentiment", analyze_sentiment)
    
    # Define the edges
    workflow.add_edge("summarize", "nature")
    workflow.add_edge("nature", "urgency")
    workflow.add_edge("urgency", "sentiment")
    workflow.set_entry_point("summarize")
    workflow.set_finish_point("sentiment")
    
    # Compile and run the graph
    app = workflow.compile()
    final_state = app.invoke(initial_state)
    
    # Convert to JSON-serializable format
    return json.loads(json.dumps(final_state, default=email_parser.json_serial))
