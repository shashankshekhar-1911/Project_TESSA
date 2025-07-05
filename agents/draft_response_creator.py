import json
from typing import List, Dict, Optional, Union, Any
from config import groq_client
from database_utils import execute_query
from zendesk_utils import post_zendesk_comment, get_zendesk_ticket_assignee, get_zendesk_id_from_ticket

def get_ticket_data(ticket_id: int) -> Optional[Dict]:
    """
    Get ticket information from tickets_ticket table
    
    Args:
        ticket_id (int): The ticket ID to query for
        
    Returns:
        Dict: Ticket data including description, support_theme, and organization_id
    """
    query = """
        SELECT description, support_theme, organization_id 
        FROM tickets_ticket 
        WHERE ticket_id = %s
    """
    
    try:
        result = execute_query(query, (ticket_id,), fetch_one=True)
        if result:
            return dict(result)
        else:
            print(f"No ticket found with ID: {ticket_id}")
            return None
            
    except Exception as e:
        print(f"Error querying tickets_ticket table: {str(e)}")
        return None

def get_organization_name(organization_id: int) -> Optional[str]:
    """
    Get organization name from tickets_organization table
    
    Args:
        organization_id (int): The organization ID to query for
        
    Returns:
        str: Organization name or None if not found
    """
    query = """
        SELECT name 
        FROM tickets_organization 
        WHERE id = %s
    """
    
    try:
        result = execute_query(query, (organization_id,), fetch_one=True)
        if result:
            return result['name']
        else:
            print(f"No organization found with ID: {organization_id}")
            return None
            
    except Exception as e:
        print(f"Error querying tickets_organization table: {str(e)}")
        return None

def get_required_inputs_from_audit(ticket_id: int) -> List[str]:
    """
    Get required inputs from tessa_audit_logs table
    
    Args:
        ticket_id (int): The ticket ID to find audit logs for
        
    Returns:
        List[str]: List of required inputs from the most recent audit log
    """
    # Get the most recent audit log for this ticket that has required_inputs
    query = """
        SELECT message->>'required_inputs' as required_inputs
        FROM tessa_audit_logs 
        WHERE ticket_id = %s 
        AND message->>'required_inputs' IS NOT NULL
        AND function = 'completeness_checker'
        ORDER BY timestamp DESC
        LIMIT 1
    """
    
    try:
        result = execute_query(query, (ticket_id,), fetch_one=True)
        
        if result and result['required_inputs']:
            try:
                # Parse the required_inputs - could be JSON string or comma-separated
                required_inputs_str = result['required_inputs']
                
                # Try to parse as JSON first
                try:
                    if required_inputs_str.startswith('[') or required_inputs_str.startswith('{'):
                        parsed_inputs = json.loads(required_inputs_str)
                        if isinstance(parsed_inputs, list):
                            return parsed_inputs
                        elif isinstance(parsed_inputs, dict):
                            # If it's a dict, extract values that look like questions
                            return [str(v) for v in parsed_inputs.values() if isinstance(v, str)]
                except json.JSONDecodeError:
                    pass
                
                # If not JSON, try comma-separated values
                if ',' in required_inputs_str:
                    return [item.strip() for item in required_inputs_str.split(',') if item.strip()]
                
                # If single string, return as single-item list
                return [required_inputs_str.strip()]
                
            except Exception as e:
                print(f"Error parsing required_inputs: {str(e)}")
                return []
        else:
            print(f"No required_inputs found for ticket ID: {ticket_id}")
            return []
            
    except Exception as e:
        print(f"Error querying tessa_audit_logs table: {str(e)}")
        return []

def draft_response_creator(ticket_id: int, 
                         model: str = "llama3-8b-8192",
                         post_to_zendesk: bool = True) -> str:
    """
    Generate a draft customer support response using Groq's Llama LLM
    Fetches all required data from PostgreSQL database tables
    Optionally posts the response to ZenDesk as a comment
    
    Args:
        ticket_id (int): The ticket ID to generate response for
        model (str): Groq model to use (default: llama3-8b-8192)
        post_to_zendesk (bool): Whether to post the response to ZenDesk (default: False)
        
    Returns:
        str: Generated draft response for customer support
    """
    
    # Fetch required inputs (questions) from tessa_audit_logs
    questions = get_required_inputs_from_audit(ticket_id)
    if not questions:
        return f"Error: No required inputs found for ticket ID {ticket_id}."
    
    # Fetch ticket data from tickets_ticket table
    ticket_data = get_ticket_data(ticket_id)
    if not ticket_data:
        return f"Error: No ticket data found for ticket ID {ticket_id}."
    
    ticket_description = ticket_data.get('description')
    support_theme = ticket_data.get('support_theme')
    organization_id = ticket_data.get('organization_id')
    
    # Fetch customer name from tickets_organization table
    customer_name = None
    if organization_id:
        customer_name = get_organization_name(organization_id)
    
    print(f"Processing ticket {ticket_id}:")
    print(f"- Found {len(questions)} required inputs")
    print(f"- Support theme: {support_theme}")
    print(f"- Customer organization: {customer_name}")
    print(f"- Description length: {len(ticket_description) if ticket_description else 0} characters")
    
    # Prepare the context with questions
    questions_context = "\n".join([f"- {question}" for question in questions])
    
    # Build the system prompt for the customer support agent role
    system_prompt = """You are an experienced and empathetic customer support agent. Your role is to:

1. Acknowledge the customer's support request professionally and warmly
2. Show empathy and understanding for their situation
3. Ask relevant follow-up questions to gather necessary information
4. Maintain a helpful, professional, and solution-oriented tone
5. Keep responses concise but comprehensive
6. Use clear, jargon-free language that customers can easily understand

Guidelines:
- Always start by acknowledging their request and thanking them for reaching out
- Ask the provided questions naturally within the context of your response and inform that this will fast-track resolution
- Use a warm but professional tone throughout"""

    # Build the user prompt with context
    user_prompt_parts = []
    
    user_prompt_parts.append("Please generate a customer support response with the following requirements:")
    
    if ticket_description:
        user_prompt_parts.append(f"\nOriginal Customer Issue:\n{ticket_description}")
    
    if support_theme:
        user_prompt_parts.append(f"\nSupport Category: {support_theme}")
    
    if customer_name:
        user_prompt_parts.append(f"\nCustomer Name: {customer_name}")
    
    user_prompt_parts.append(f"\nImportant: You must ask these specific questions as part of your response:\n{questions_context}")
    
    user_prompt_parts.append("""
Requirements for the response:
1. Start with a warm acknowledgment and thanks
2. Show empathy for their situation
3. Naturally incorporate ALL the provided questions into your response
4. Maintain a professional yet friendly tone
5. End with reassurance about helping them resolve the issue
6. Keep the response concise but complete (aim for 2-3 paragraphs)

Generate the complete customer support response now.""")
    
    user_prompt = "\n".join(user_prompt_parts)
    
    try:
        # Call Groq API to generate the response
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            temperature=0.2,  # Balanced creativity and consistency
            max_tokens=2000,  # Reasonable length for support responses
            top_p=0.9
        )
        
        # Extract the generated response
        generated_response = chat_completion.choices[0].message.content.strip()
        
        print(f"Successfully generated draft response using {model}")
        
        # Post to ZenDesk if requested
        if post_to_zendesk:
            try:
                print("🔄 Attempting to post draft response to ZenDesk...")
                
                # Get ZenDesk ticket ID from internal ticket ID
                zendesk_ticket_id = get_zendesk_id_from_ticket(ticket_id)
                
                if zendesk_ticket_id:
                    # Get assignee information
                    assignee_info = get_zendesk_ticket_assignee(zendesk_ticket_id)
                    
                    # Construct the comment with the exact format requested
                    if assignee_info and assignee_info.get('name'):
                        assignee_name = assignee_info['name']
                        comment_body = f"""{assignee_name},
You can consider the following response as an initial draft for your first response

{generated_response}"""
                    else:
                        print("⚠️  No assignee found - posting comment without assignee mention")
                        comment_body = f"""You can consider the following response as an initial draft for your first response

{generated_response}"""
                    
                    # Post comment to ZenDesk
                    zendesk_success = post_zendesk_comment(
                        zendesk_ticket_id=zendesk_ticket_id,
                        comment_body=comment_body,
                        public=False  # Internal comment
                    )
                    
                    if zendesk_success:
                        print(f"✅ Draft response successfully posted to ZenDesk ticket {zendesk_ticket_id}")
                    else:
                        print(f"❌ Failed to post draft response to ZenDesk ticket {zendesk_ticket_id}")
                else:
                    print(f"⚠️  No ZenDesk ticket ID found for internal ticket {ticket_id}")
                    
            except Exception as zendesk_error:
                print(f"⚠️  ZenDesk integration error: {str(zendesk_error)}")
                print("📝 Draft response generated successfully, but ZenDesk posting failed")
                # Continue execution even if ZenDesk posting fails
        
        return generated_response
        
    except Exception as e:
        error_message = f"Error generating response with Groq: {str(e)}"
        print(error_message)
        return f"I apologize, but I'm currently unable to generate a response due to a technical issue. Please try again shortly. Error: {str(e)}"

def process_draft_response_creator(ticket_id: int, 
                                 model: str = "llama3-8b-8192",
                                 post_to_zendesk: bool = True) -> Dict[str, Any]:
    """
    Process draft response creation for a ticket and log to audit table
    This is the main function called by webhooks with audit logging
    
    Args:
        ticket_id (int): The ticket ID to process
        model (str): Groq model to use (default: llama3-8b-8192)
        post_to_zendesk (bool): Whether to post the response to ZenDesk (default: False)
        
    Returns:
        Dict[str, Any]: The response data with audit information
    """
    # Call the draft_response_creator function with the actual ticket ID as an argument
    generated_response = draft_response_creator(ticket_id, model, post_to_zendesk)
    
    # Get additional ticket data for context
    ticket_data = get_ticket_data(ticket_id)
    support_theme = ticket_data.get('support_theme', '') if ticket_data else ''
    description = ticket_data.get('description', '') if ticket_data else ''
    
    # Prepare the response data
    response_data = {
        'ticket_id': ticket_id,
        'generated_response': generated_response,
        'support_theme': support_theme,
        'description': description,
        'model_used': model,
        'response_length': len(generated_response) if generated_response else 0
    }
    
    # We get the generated_response that needs to go into the tessa_audit_logs table 
    # under the message column. Put the argument ticket_id in ticket_id column of the table 
    # and assign function as "draft_response_creator"
    try:
        from tickets.utils import log_audit_event
        
        audit_log = log_audit_event(
            function_name="draft_response_creator",
            ticket_id=ticket_id,
            response_data=generated_response,
        )
        
        print(f"Draft response logged to audit table for ticket {ticket_id}")
        
        # Add audit info to response data
        response_data['audit_logged'] = True
        if audit_log:
            response_data['audit_id'] = str(audit_log.audit_id)
            
    except Exception as e:
        print(f"Error logging draft response to audit table: {str(e)}")
        response_data['audit_logged'] = False
        response_data['audit_error'] = str(e)
    
    return response_data

# Example usage and testing function
def test_draft_response_creator():
    """
    Test function to demonstrate the draft response creator functionality
    """
    # Test with a real ticket ID - you'll need to replace with an actual ticket ID from your database
    test_ticket_id = 925  # Replace with actual ticket ID
    
    print("=== Draft Response Creator Test ===")
    print(f"Testing with Ticket ID: {test_ticket_id}")
    print("\n--- Fetching Data from Database ---")
    
    # Test individual functions first
    print("1. Testing required inputs fetch...")
    questions = get_required_inputs_from_audit(test_ticket_id)
    print(f"   Required inputs: {questions}")
    
    print("2. Testing ticket data fetch...")
    ticket_data = get_ticket_data(test_ticket_id)
    print(f"   Ticket data: {ticket_data}")
    
    if ticket_data and ticket_data.get('organization_id'):
        print("3. Testing organization name fetch...")
        org_name = get_organization_name(ticket_data['organization_id'])
        print(f"   Organization name: {org_name}")
    
    print("\n--- Generated Response ---")
    
    # Generate response using the refactored function
    # Set post_to_zendesk=True to test ZenDesk integration
    response = draft_response_creator(test_ticket_id, post_to_zendesk=False)
    print(response)
    
    print("\n--- ZenDesk Integration Test ---")
    print("To test ZenDesk integration, set post_to_zendesk=True in the function call above")
    print("Make sure your .env file has ZenDesk credentials configured")

def test_with_manual_data():
    """
    Alternative test function that uses the old-style manual data input
    This is useful for testing when you don't have database access
    """
    print("=== Manual Data Test (Fallback) ===")
    
    # Simulate database data
    test_questions = [
        "What browser are you using?",
        "What error message exactly are you seeing?",
        "When did this issue first start occurring?",
        "Have you tried clearing your browser cache and cookies?"
    ]
    
    # You could modify this to test the individual components
    print("Manual test data:")
    print(f"Questions: {test_questions}")
    print("Note: Use test_draft_response_creator() with actual database data for full testing")

if __name__ == "__main__":
    # Test with database integration
    test_draft_response_creator()
    print("\n" + "="*50 + "\n")
    # Fallback manual test
    test_with_manual_data() 

#TEMPORARY CODE FOR SHASHANK TO PROVIDE INSTRUCTIONS
#   Call the draft_response_creator function with the actual ticket ID as an argument
#   We get the generated_response that needs to go into the tessa_audit_logs table under the message
#   column. Put the argument ticket_id in ticket_id column of the table and assign function as 
#   "draft_response_creator"
#         report = {
#         'ticket_id': ticket_id,
#         'support_theme': support_theme,
#         'description': description,
#         'required_inputs': required_inputs,
#         'missing_inputs': missing_inputs,
#         'completeness_score': round(completeness_score, 2),
#     }