import re
from typing import List, Dict, Any, Optional
from database_utils import get_db_cursor, execute_query

def input_checklist(support_theme: str) -> List[str]:
    """
    Retrieve a list of high-priority information items needed for a specific support theme
    
    Args:
        support_theme (str): The support theme to query for
        
    Returns:
        List[str]: List of input items with high priority for the given support theme
    """
    # Query the input_needed_checklist table for high priority items
    query = """
        SELECT input_needed
        FROM tickets_inputneededchecklist 
        WHERE support_theme = %s AND priority = 'high'
        ORDER BY input_needed
    """
    
    try:
        results = execute_query(query, (support_theme,))
        if results:
            # Extract input items from query results
            input_items = [row['input_needed'] for row in results]
            print(f"Found {len(input_items)} high-priority input items for theme '{support_theme}'")
            return input_items
        else:
            print(f"No high-priority inputs found for theme '{support_theme}'")
            return []
            
    except Exception as e:
        print(f"Error querying inputneededchecklist table: {str(e)}")
        return []

def inputs_required(description: str, support_theme: str) -> List[str]:
    """
    Compare the ticket description against the required inputs checklist to identify missing items
    
    Args:
        description (str): The support ticket description to analyze
        support_theme (str): The support theme for which to get the checklist
        
    Returns:
        List[str]: List of required input items that are missing from the description
    """
    # Get the checklist of required inputs for this support theme
    required_inputs = input_checklist(support_theme)
    
    if not required_inputs:
        print(f"No required inputs found for support theme: {support_theme}")
        return []
    
    # Convert description to lowercase for case-insensitive matching
    description_lower = description.lower()
    
    # List to store missing input items
    missing_inputs = []
    
    # Check each required input item against the description
    for input_item in required_inputs:
        # Create variations of the input item for flexible matching
        input_variations = [
            input_item.lower(),
            input_item.lower().replace(' ', ''),  # Remove spaces
            input_item.lower().replace('_', ' '),  # Replace underscores with spaces
            input_item.lower().replace('-', ' '),  # Replace hyphens with spaces
        ]
        
        # Check if any variation of the input item is mentioned in the description
        found = False
        for variation in input_variations:
            # Use word boundaries to avoid partial matches
            if re.search(r'\b' + re.escape(variation) + r'\b', description_lower):
                found = True
                break
            # Also check for partial matches without word boundaries for compound terms
            elif variation in description_lower:
                found = True
                break
        
        # If the input item is not found in the description, add it to missing list
        if not found:
            missing_inputs.append(input_item)
    
    print(f"Analysis complete: {len(missing_inputs)} out of {len(required_inputs)} required inputs are missing")
    
    return missing_inputs

def get_ticket_details(ticket_id: int) -> Optional[Dict[str, Any]]:
    """
    Get ticket details from tickets_ticket table
    
    Args:
        ticket_id (int): The ticket ID to query for
        
    Returns:
        Dict[str, Any]: Ticket details including description and support_theme, or None if not found
    """
    query = """
        SELECT description, support_theme 
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

def get_completeness_report(ticket_id: int) -> Dict[str, Any]:
    """
    Generate a comprehensive completeness report for a support ticket
    Fetches ticket details from the database using the ticket ID
    
    Args:
        ticket_id (int): The ticket ID to analyze
        
    Returns:
        Dict[str, Any]: Comprehensive report including required inputs, missing inputs, and completeness score
    """
    # Fetch ticket details from database
    ticket_details = get_ticket_details(ticket_id)
    if not ticket_details:
        return {
            'error': f'No ticket found with ID: {ticket_id}',
            'ticket_id': ticket_id,
            'completeness_score': 0
        }
    
    description = ticket_details.get('description', '')
    support_theme = ticket_details.get('support_theme', '')
    
    if not description:
        print(f"Warning: No description found for ticket ID: {ticket_id}")
    
    if not support_theme:
        print(f"Warning: No support theme found for ticket ID: {ticket_id}")
        return {
            'error': f'No support theme found for ticket ID: {ticket_id}',
            'ticket_id': ticket_id,
            'description': description,
            'completeness_score': 0
        }
    
    # Generate completeness analysis
    required_inputs = input_checklist(support_theme)
    missing_inputs = inputs_required(description, support_theme)
    
    # Calculate completeness score as percentage
    total_required = len(required_inputs)
    total_missing = len(missing_inputs)
    completeness_score = ((total_required - total_missing) / total_required * 100) if total_required > 0 else 100
    
    report = {
        'ticket_id': ticket_id,
        'support_theme': support_theme,
        'description': description,
        'required_inputs': required_inputs,
        'missing_inputs': missing_inputs,
        'completeness_score': round(completeness_score, 2),
    }
    
    return report

def process_completeness_check(ticket_id: int) -> Dict[str, Any]:
    """
    Process completeness check for a ticket and log to audit logs table
    
    Args:
        ticket_id (int): The ticket ID to process
        
    Returns:
        Dict[str, Any]: The completeness report
    """
    # Call the get_completeness_report function with the actual ticket ID as an argument
    report = get_completeness_report(ticket_id)
    
    # We get the following json that needs to go into the tessa_audit_logs table
    # Put the entire json in message column, report.ticket_id in ticket_id column
    # and assign function as "completeness_checker"
    try:
        from tickets.utils import log_audit_event
        
        audit_log = log_audit_event(
            function_name="completeness_checker",
            ticket_id=report['ticket_id'],
            response_data=report,
        )
        
        print(f"Completeness check logged to audit table for ticket {ticket_id}")
        
        # Add audit info to report
        report['audit_logged'] = True
        if audit_log:
            report['audit_id'] = str(audit_log.audit_id)
            
    except Exception as e:
        print(f"Error logging completeness check to audit table: {str(e)}")
        report['audit_logged'] = False
        report['audit_error'] = str(e)
    
    return report

# Example usage and testing function
def test_completeness_checker():
    """
    Test function to demonstrate the completeness checker functionality
    """
    # Test with a real ticket ID - you'll need to replace with an actual ticket ID from your database
    test_ticket_id = 925  # Replace with actual ticket ID
    
    print("=== Completeness Checker Test ===")
    print(f"Testing with Ticket ID: {test_ticket_id}")
    print("\n--- Fetching Ticket Details ---")
    
    # Test ticket details fetch
    ticket_details = get_ticket_details(test_ticket_id)
    if ticket_details:
        print(f"Support Theme: {ticket_details.get('support_theme')}")
        print(f"Description: {ticket_details.get('description', '')[:100]}...")  # First 100 chars
        
        support_theme = ticket_details.get('support_theme')
        description = ticket_details.get('description', '')
        
        print("\n--- Required Inputs ---")
        required = input_checklist(support_theme)
        for item in required:
            print(f"- {item}")
        
        print("\n--- Missing Inputs ---")
        missing = inputs_required(description, support_theme)
        for item in missing:
            print(f"- {item}")
    else:
        print("Could not fetch ticket details")
    
    print("\n--- Completeness Report ---")
    report = get_completeness_report(test_ticket_id)
    for key, value in report.items():
        if key == 'description' and isinstance(value, str) and len(value) > 100:
            print(f"{key}: {value[:100]}...")  # Truncate long descriptions
        else:
            print(f"{key}: {value}")

def test_with_manual_data():
    """
    Alternative test function for testing individual functions with manual data
    This is useful when you don't have database access
    """
    print("=== Manual Data Test (Individual Functions) ===")
    
    test_support_theme = "Work Status Reversion"
    test_description = """
    User is unable to login to the system. They are getting an error message 
    saying 'Invalid credentials'. The user confirmed their username is correct.
    Browser being used is Chrome version 98. Operating system is Windows 10.
    """
    
    print(f"Support Theme: {test_support_theme}")
    print(f"Description: {test_description}")
    
    print("\n--- Testing input_checklist function ---")
    required = input_checklist(test_support_theme)
    print(f"Required inputs: {required}")
    
    print("\n--- Testing inputs_required function ---")
    missing = inputs_required(test_description, test_support_theme)
    print(f"Missing inputs: {missing}")
    
    print("\nNote: Use test_completeness_checker() with actual database data for full testing")

if __name__ == "__main__":
    # Test with database integration
    test_completeness_checker()
    print("\n" + "="*50 + "\n")
    # Fallback manual test
    test_with_manual_data() 

#TEMPORARY CODE FOR SHASHANK TO PROVIDE INSTRUCTIONS
#   Call the get_completeness_report function with the actual ticket ID as an argument
#   We get the following json that needs to go into the tessa_audit_logs table. Put the entire json in
#   message column. Put report.ticket_id in ticket_id column of the table and assign function as "completeness_checker"
#         report = {
#         'ticket_id': ticket_id,
#         'support_theme': support_theme,
#         'description': description,
#         'required_inputs': required_inputs,
#         'missing_inputs': missing_inputs,
#         'completeness_score': round(completeness_score, 2),
#     }