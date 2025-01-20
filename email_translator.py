#Extracts relevant context from a client's email

#Importing modules
import os
import phi
import json
import email_parser
from phi.agent import Agent
from phi.model.groq import Groq


#Initialise the agent
decodingClientEmailAgent = Agent(
    name="Understanding Client Email Agent",
    model = Groq(id="llama-3.3-70b-versatile"),
    description="""You read client's email to understand if they're queries and how they should be handled based on 
    nature, urgency, sentiment, etc.""",
    instructions=["When given a set of options, respond by selecting one of the available options and do not mention anything else",
    "When asked to summarise an ask, use an infinitive form of the verb at the start of the response to capture the actionable",
    "Avoid having any headers in the response"],
    markdown=True,
    debug_mode=False,
)

def decode_client_email(email_metadata):
    body = email_metadata.get("body","")
 
     # Summarise the ask in 1 line
    querySummary = decodingClientEmailAgent.run(f"""What would be a fair 1 line summary of the ask that captures what is requested by the 
    client as per the following email -  {body}""").content

    # Copy paste the email body in the description box
    queryDescription = body
    
    # Check if the email is a product query, bug reporting, new request or just FYI   
    queryNature = decodingClientEmailAgent.run(f"""What's the nature of the following email received from the client? Please 
    select one of the following only - Query, Bug Reporting, New Request or Just FYI. 
    {body}""").content

    # Extract queryUrgency
    queryUrgency = decodingClientEmailAgent.run(f"""What's the urgency of the ask by the client as per the following email 
    from the client? Please select one of the following only - High, Medium, Low. 
    {body}""").content

    # Extract querySentiment
    querySentiment = decodingClientEmailAgent.run(f"""What's the sentiment of the tone used by the client as per the following 
    email from the client? Please select one of the following only - Extremely Positive, Positive, Neutral, Negative, 
    Extremely Negative.
    {body}""").content

    email_context = {
        "querySummary": querySummary,
        "queryDescription": queryDescription,
        "queryNature": queryNature,
        "queryUrgency": queryUrgency,
        "querySentiment": querySentiment
    }
    return json.loads(json.dumps(email_context, default=email_parser.json_serial))
