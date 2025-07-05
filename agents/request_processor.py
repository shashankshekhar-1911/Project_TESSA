#Extracts relevant context from a client's email

#Importing modules
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import json
from typing import TypedDict, Annotated, Sequence, Union
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from rag.query_rag import query_rag, intermediate_query_rag


# Define the state type
class ticketState(TypedDict):
    body: str
    priority: Union[dict, None]
    organization_id: Union[dict, None]
    product: Union[dict, None]
    support_theme: Union[dict, None]
    summary: Union[dict, None]
    severity: Union[dict, None]
    ticket_type: Union[dict, None]
    interface_affected: Union[dict, None]
    code_change: Union[dict, None]
    module: Union[dict, None]
    workaround: Union[dict, None]
    effort_aidash: Union[dict, None]
    urgency: Union[dict, None]
    system_prompt: str

# Initialize the LLM
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# Define the prompts
def get_system_prompt_with_context(ticket_body: str) -> str:
    """Generate system prompt with RAG context."""
    # Get relevant context from RAG
    rag_context = intermediate_query_rag(ticket_body)
    
    return f"""You are an AI assistant that analyzes support tickets and extracts various attributes. 
You have access to relevant historical context that may help in your analysis:

Historical Context:
{rag_context}

For each attribute, provide your response in JSON format with two fields:
- value: The selected value from the allowed options
- reasoning: A brief explanation (2-3 sentences maximum) of why you chose this value

IMPORTANT: Your response must be ONLY the JSON object with value and reasoning fields. Do not include any additional text, analysis, or explanation outside the JSON object.

Allowed options for each field:
1. Priority: How quickly the issue needs to be addressed (Low, Normal, High, Urgent)
2. Organization: The company or entity submitting the ticket (Organization name/ID if present, or 'Unknown')
3. Product: The specific software product affected (IVMS, BNGAI, CRIS, AIMS, IEMS). In case you are unable to determine the product use 'IVMS' as default value.
4. Support Theme: The primary category of the support request. This is extremely critical. Only use one of the following support themes and their definitions, based on historical analysis:

   - Work Status Reversion: Work items previously marked as completed revert to an incomplete state.
   - Access and Login Issues: Problems logging in, callback URL mismatches, or inability to access the system.
   - User Management: Issues such as role changes, users not appearing, or crew assignment problems.
   - Bulk Assignment/Reassignment of Work: Requests or issues related to bulk un-assignment, reassignment, or assignment of work items.
   - Syncing and Offline Data Issues: Data not syncing correctly, offline changes not reflected, or sync failures.
   - Time Entry and Timesheet Errors: Incorrect time entries (e.g., AM/PM errors, duplicate entries, or missing timesheets).
   - Data Discrepancies: API/UI mismatches, Span ID issues, or mismatches between displayed and actual data.
   - Performance Issues: Significant delays or lags when applying filters, loading data, or using the system.
   - Layer and Imagery Issues: Problems with property boundaries not matching parcels, or issues with map layers/imagery.
   - Task/Work Progress Calculation Errors: Progress bars or completion percentages not updating or showing incorrect values.

5. Severity: The impact level of the issue on customer's business operations (low, medium, critical, blocker)
6. Ticket Type: The nature of the request (bug, user_mgmt, work_mgmt, business/product_knowledge, non_issues)
7. Interface Affected: The user interface components impacted (Web Interface, Mobile App, API, Multiple, or Unknown)
8. Code Change: The system components requiring modifications (Database, Backend, Frontend-Web, Frontend-Mobile, API, Multiple, or Unknown)
9. Module: The specific functional area affected (Cycle Trim, Risk Module, Work Management, Hazard Tree, or Unknown)
10. Workaround: Whether a temporary solution from our side exists (No, Semi, Full, or Unknown)
11. Effort: The estimated work required to resolve (High, Medium, Low, or Unknown)
12. Urgency: The time sensitivity of the request (Immediate, High, Medium, Low)

Example response format:
{{
    "value": "High",
    "reasoning": "The issue affects multiple users and impacts critical functionality"
}}"""

# Create prompt templates for each field
priority_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What's the priority level of the following ticket? {body}")
])

organization_id_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What organization is this ticket from? {body}")
])

product_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "Which product is this ticket related to? {body}")
])

support_theme_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What is the main theme of this support ticket? Choose from: Work Status Reversion, Access and Login Issues, User Management, Bulk Assignment/Reassignment of Work, Syncing and Offline Data Issues, Time Entry and Timesheet Errors, Data Discrepancies, Performance Issues, Layer and Imagery Issues, Task/Work Progress Calculation Errors. {body}")
])

summary_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "Provide a concise one-line summary (max 100 characters) of this ticket. Focus on the core issue or request. {body}")
])

severity_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What is the severity level of the issue described in this ticket? {body}")
])

ticket_type_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What type of ticket is this? {body}")
])

interface_affected_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "Which interface is affected by the issue described in this ticket? {body}")
])

code_change_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "Which system component requires code changes to resolve this ticket? Choose from: Database, Backend, Frontend-Web, Frontend-Mobile, API, Multiple, or Unknown. {body}")
])

module_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "Which module is affected by the issue described in this ticket? {body}")
])

workaround_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "Is there a workaround available for the issue described in this ticket? {body}")
])

effort_aidash_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What is the estimated effort required to resolve this ticket? {body}")
])

urgency_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    ("human", "What is the urgency level of this ticket? {body}")
])

def process_ticket(ticket_metadata: dict) -> dict:
    """Process the ticket metadata and return the analyzed context."""
    # Get the ticket body
    ticket_body = ticket_metadata.get("plain_body", "")
    
    # Generate system prompt with RAG context
    system_prompt = get_system_prompt_with_context(ticket_body)
    
    # Initialize the state
    initial_state: ticketState = {
        "body": ticket_body,
        "system_prompt": system_prompt,  # Add system prompt to state
        "priority": None,
        "organization_id": None,
        "product": None,
        "support_theme": None,
        "summary": None,
        "severity": None,
        "ticket_type": None,
        "interface_affected": None,
        "code_change": None,
        "module": None,
        "workaround": None,
        "effort_aidash": None,
        "urgency": None
    }
    
    # Create the workflow
    workflow = StateGraph(ticketState)
    
    # Add nodes
    workflow.add_node("determine_priority", determine_priority)
    workflow.add_node("identify_organization", identify_organization)
    workflow.add_node("identify_product", identify_product)
    workflow.add_node("categorize_theme", categorize_theme)
    workflow.add_node("summarize_ticket", summarize_ticket)
    workflow.add_node("determine_severity", determine_severity)
    workflow.add_node("identify_ticket_type", identify_ticket_type)
    workflow.add_node("identify_interface", identify_interface)
    workflow.add_node("assess_code_change", assess_code_change)
    workflow.add_node("identify_module", identify_module)
    workflow.add_node("check_workaround", check_workaround)
    workflow.add_node("estimate_effort", estimate_effort)
    workflow.add_node("assess_urgency", assess_urgency)
        
    # Define the edges
    workflow.add_edge("determine_priority", "identify_organization")
    workflow.add_edge("identify_organization", "identify_product")
    workflow.add_edge("identify_product", "categorize_theme")
    workflow.add_edge("categorize_theme", "summarize_ticket")
    workflow.add_edge("summarize_ticket", "determine_severity")
    workflow.add_edge("determine_severity", "identify_ticket_type")
    workflow.add_edge("identify_ticket_type", "identify_interface")
    workflow.add_edge("identify_interface", "assess_code_change")
    workflow.add_edge("assess_code_change", "identify_module")
    workflow.add_edge("identify_module", "check_workaround")
    workflow.add_edge("check_workaround", "estimate_effort")
    workflow.add_edge("estimate_effort", "assess_urgency")
    
    workflow.set_entry_point("determine_priority")
    workflow.set_finish_point("assess_urgency")
    
    # Compile and run the graph
    graph = workflow.compile()
    final_state = graph.invoke(initial_state)


    '''
    Sample Output:
    final_state = { 
    
    'body': 'The user is experiencing a duplicated time entry issue on their time entry for 3-04-2025, which is showing 11 hours instead of the expected 10 hours due to a duplicated entry. The user is seeking assistance to correct the issue.',
    
    'code_change': {   'reasoning': 'The issue is related to a duplicated time '
                                    'entry, which suggests a problem with data '
                                    'storage or retrieval, making the Database '
                                    'component the most likely to require code '
                                    'changes to resolve the ticket.',
                       'value': 'Database'},
    'effort_aidash': {   'reasoning': 'The issue is a simple case of a '
                                      'duplicated time entry, which can be '
                                      'easily corrected by removing the '
                                      'duplicate entry, and the user is only '
                                      'reporting a 1-hour discrepancy in their '
                                      'time entry for the day.',
                         'value': 'Low'},
    'interface_affected': {   'reasoning': 'The issue described in the ticket '
                                           'is related to a time entry '
                                           'duplication on the web interface, '
                                           'and the user is able to view and '
                                           'report the issue through the web '
                                           'interface.',
                              'value': 'Web Interface'},
    'module': {   'reasoning': 'The issue described is related to time entry '
                               'and work assignment, which falls under the '
                               'work management module. The user is '
                               'experiencing a duplicated time entry issue, '
                               'which affects their work hours and needs to be '
                               'corrected.',
                  'value': 'Work Management'},
    'organization_id': {   'reasoning': "The user's email address is "
                                        'CORILEY@asplundh.com, indicating that '
                                        'the ticket is from Asplundh '
                                        'organization.',
                           'value': 'Asplundh'},
    'priority': {   'reasoning': 'The issue is a duplicated time entry, which '
                                 'is causing an incorrect total hour count, '
                                 'but it does not appear to be critical or '
                                 'urgent, and the user is still able to report '
                                 'the issue and request assistance.',
                    'value': 'Normal'},
    'product': {   'reasoning': 'The provided text does not explicitly mention '
                                'a specific product related to the issue, and '
                                'the conversation appears to be about '
                                'resolving time entry and work assignment '
                                'issues, but it does mention AiDash Support '
                                'and grant@aidash.com, suggesting a potential '
                                'connection to the AiDash product, however, '
                                "it's not explicitly stated.",
                   'value': 'Unknown'},
    'severity': {   'reasoning': "The issue affects the user's time entry, "
                                 'resulting in an incorrect total of 11 hours '
                                 'instead of 10 hours due to a duplicated '
                                 'entry, but it does not seem to have a '
                                 'critical impact on the overall business '
                                 'operations.',
                    'value': 'medium'},
    'summary': {   'reasoning': "The user's time entry for 3-04-2025 is "
                                'showing 11 hours instead of 10 hours due to a '
                                'duplicated entry.',
                   'value': 'Duplicated time entry'},
    'support_theme': {   'reasoning': 'The user is experiencing a technical '
                                      'issue with their time entry for '
                                      '3-04-2025, which is showing 11 hours '
                                      'instead of the expected 10 hours due to '
                                      'a duplicated entry, requiring '
                                      'assistance to correct the issue.',
                         'value': 'Technical Issue'},
    'system_prompt': 'You are an AI assistant that analyzes support tickets '
                     'and extracts various attributes. \n'
                     'You have access to relevant historical context that may '
                     'help in your analysis:\n'
                     '\n'
                     'Historical Context:\n'
                     'The question is not explicitly stated in the provided '
                     'context. However, based on the information given, it '
                     'appears that the user is experiencing an issue with '
                     'their time entry for 3-04-2025, which is showing 11 '
                     'hours instead of the expected 10 hours due to a '
                     'duplicated entry.\n'
                     '\n'
                     'To address this issue, the user should follow these '
                     'steps:\n'
                     '\n'
                     '1. Review their time entries for 3-04-2025 to identify '
                     'the duplicated entry.\n'
                     '2. Check the work ID associated with the duplicated '
                     'entry to ensure it is correct.\n'
                     '3. Contact their IT team or the AiDash support team to '
                     'report the issue and request assistance in correcting '
                     'the duplicated entry.\n'
                     '\n'
                     'Additionally, the user should be cautious when receiving '
                     'emails from external senders and avoid clicking on links '
                     'or opening attachments from unknown or suspicious '
                     'sources. They should also not provide their user ID or '
                     'password in response to any email requests.\n'
                     '\n'
                     'For each attribute, provide your response in JSON format '
                     'with two fields:\n'
                     '- value: The selected value from the allowed options\n'
                     '- reasoning: A brief explanation (2-3 sentences maximum) '
                     'of why you chose this value\n'
                     '\n'
                     'IMPORTANT: Your response must be ONLY the JSON object '
                     'with value and reasoning fields. Do not include any '
                     'additional text, analysis, or explanation outside the '
                     'JSON object.\n'
                     '\n'
                     'Allowed options for each field:\n'
                     '1. Priority: How quickly the issue needs to be addressed '
                     '(Low, Normal, High, Urgent)\n'
                     '2. Organization: The company or entity submitting the '
                     "ticket (Organization name/ID if present, or 'Unknown')\n"
                     '3. Product: The specific software product affected '
                     "(IVMS, BNGAI, CRIS, AIMS, IEMS, or 'Unknown')\n"
                     '4. Support Theme: The primary category of the support '
                     'request (Technical Issue, Feature Request, Account '
                     'Management, Billing, or General Inquiry)\n'
                     "5. Severity: The impact level of the issue on customer's "
                     'business operations (low, medium, critical, blocker)\n'
                     '6. Ticket Type: The nature of the request (bug, '
                     'user_mgmt, work_mgmt, business/product_knowledge, '
                     'non_issues)\n'
                     '7. Interface Affected: The user interface components '
                     'impacted (Web Interface, Mobile App, API, Multiple, or '
                     'Unknown)\n'
                     '8. Code Change: The system components requiring '
                     'modifications (Database, Backend, Frontend-Web, '
                     'Frontend-Mobile, API, Multiple, or Unknown)\n'
                     '9. Module: The specific functional area affected (Cycle '
                     'Trim, Risk Module, Work Management, Hazard Tree, or '
                     'Unknown)\n'
                     '10. Workaround: Whether a temporary solution from '
                     'ourside exists (No, Semi, Full, or Unknown)\n'
                     '11. Effort: The estimated work required to resolve '
                     '(High, Medium, Low, or Unknown)\n'
                     '12. Urgency: The time sensitivity of the request '
                     '(Immediate, High, Medium, Low)\n'
                     '\n'
                     'Example response format:\n'
                     '{\n'
                     '    "value": "High",\n'
                     '    "reasoning": "The issue affects multiple users and '
                     'impacts critical functionality"\n'
                     '}',
    'ticket_type': {   'reasoning': 'The issue is related to a duplicated time '
                                    'entry, which is a technical issue with '
                                    'the system, and the user is reporting an '
                                    'error with their time entry for '
                                    '3-04-2025, indicating a bug in the '
                                    'system.',
                       'value': 'bug'},
    'urgency': {   'reasoning': 'The issue is related to a duplicated time '
                                'entry, which is causing an incorrect total '
                                'hours worked, but it does not seem to be '
                                'critical or urgent, as it can be resolved by '
                                'reviewing and correcting the time entry.',
                   'value': 'Medium'},
    'workaround': {   'reasoning': 'The issue described is a duplicated time '
                                   'entry, and the user is seeking assistance '
                                   'to correct it, indicating that there is no '
                                   'known workaround available to the user to '
                                   'resolve the issue on their own.',
                      'value': 'No'}}
    '''
    

    return final_state

# Define the nodes
def determine_priority(state: ticketState) -> ticketState:
    """Generate priority level and reasoning for the email."""
    # print("Determining priority with body:", state["body"])
    response = llm.invoke(priority_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Priority response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["priority"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["priority"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def identify_organization(state: ticketState) -> ticketState:
    """Determine the organization and reasoning."""
    # print("Determining organization with body:", state["body"])
    response = llm.invoke(organization_id_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Organization response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["organization_id"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["organization_id"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def identify_product(state: ticketState) -> ticketState:
    """Identify the product and reasoning."""
    # print("Identifying product with body:", state["body"])
    response = llm.invoke(product_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Product response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["product"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["product"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def categorize_theme(state: ticketState) -> ticketState:
    """Categorize the support theme and reasoning."""
    # print("Categorizing theme with body:", state["body"])
    response = llm.invoke(support_theme_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Theme response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["support_theme"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["support_theme"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def summarize_ticket(state: ticketState) -> ticketState:
    """Generate summary and reasoning."""
    # print("Summarizing ticket with body:", state["body"])
    response = llm.invoke(summary_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Summary response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["summary"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["summary"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def determine_severity(state: ticketState) -> ticketState:
    """Determine severity level and reasoning."""
    # print("Determining severity with body:", state["body"])
    response = llm.invoke(severity_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Severity response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["severity"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["severity"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def identify_ticket_type(state: ticketState) -> ticketState:
    """Identify ticket type and reasoning."""
    # print("Identifying ticket type with body:", state["body"])
    response = llm.invoke(ticket_type_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Ticket type response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["ticket_type"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["ticket_type"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def identify_interface(state: ticketState) -> ticketState:
    """Identify affected interface and reasoning."""
    # print("Identifying interface with body:", state["body"])
    response = llm.invoke(interface_affected_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Interface response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["interface_affected"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["interface_affected"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def assess_code_change(state: ticketState) -> ticketState:
    """Determine code change needs and reasoning."""
    # print("Assessing code change need with body:", state["body"])
    response = llm.invoke(code_change_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Code change response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["code_change"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["code_change"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def identify_module(state: ticketState) -> ticketState:
    """Identify affected module and reasoning."""
    # print("Identifying module with body:", state["body"])
    response = llm.invoke(module_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Module response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["module"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["module"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def check_workaround(state: ticketState) -> ticketState:
    """Check workaround availability and reasoning."""
    # print("Checking workaround with body:", state["body"])
    response = llm.invoke(workaround_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Workaround response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["workaround"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["workaround"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def estimate_effort(state: ticketState) -> ticketState:
    """Estimate effort and reasoning."""
    # print("Estimating effort with body:", state["body"])
    response = llm.invoke(effort_aidash_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Effort response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["effort_aidash"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["effort_aidash"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state

def assess_urgency(state: ticketState) -> ticketState:
    """Assess urgency and reasoning."""
    # print("Assessing urgency with body:", state["body"])
    response = llm.invoke(urgency_prompt_template.format_messages(
        system_prompt=state.get("system_prompt", ""),
        body=state["body"]
    ))
    # print("Urgency response:", response.content)
    
    try:
        result = json.loads(response.content)
        state["urgency"] = {
            "value": result["value"],
            "reasoning": result["reasoning"]
        }
    except json.JSONDecodeError:
        state["urgency"] = {
            "value": response.content,
            "reasoning": "No reasoning provided"
        }
    return state