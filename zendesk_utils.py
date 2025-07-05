import os
import base64
import json
import requests
from typing import Dict, Optional, List
from dotenv import load_dotenv
from database_utils import execute_query

# Load environment variables
load_dotenv()

# ZenDesk API Configuration
# Add these to your .env file:
ZENDESK_URL = os.getenv('ZENDESK_URL')  # e.g., 'https://yourcompany.zendesk.com'
ZENDESK_EMAIL = os.getenv('ZENDESK_EMAIL')  # Your ZenDesk email
ZENDESK_TOKEN = os.getenv('ZENDESK_TOKEN')  # Your ZenDesk API token

class ZenDeskError(Exception):
    """Custom exception for ZenDesk API errors"""
    pass

def validate_zendesk_config() -> bool:
    """
    Validate that all required ZenDesk configuration is present
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    required_vars = [ZENDESK_URL, ZENDESK_EMAIL, ZENDESK_TOKEN]
    missing_vars = [var for var in ['ZENDESK_URL', 'ZENDESK_EMAIL', 'ZENDESK_TOKEN'] 
                   if not globals()[var]]
    
    if missing_vars:
        print(f"❌ Missing ZenDesk configuration: {', '.join(missing_vars)}")
        return False
    
    return True

def get_zendesk_headers() -> Dict[str, str]:
    """
    Get headers for ZenDesk API requests
    
    Returns:
        Dict[str, str]: Headers with authentication
        
    Raises:
        ZenDeskError: If credentials are not configured
    """
    if not validate_zendesk_config():
        raise ZenDeskError("ZenDesk credentials not found in environment variables")
    
    auth_string = f"{ZENDESK_EMAIL}/token:{ZENDESK_TOKEN}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    
    return {
        'Authorization': f'Basic {encoded_auth}',
        'Content-Type': 'application/json'
    }

def get_zendesk_ticket_details(zendesk_ticket_id: int) -> Optional[Dict]:
    """
    Get full ticket details from ZenDesk
    
    Args:
        zendesk_ticket_id (int): The ZenDesk ticket ID
        
    Returns:
        Dict: Full ticket information or None if not found
    """
    if not validate_zendesk_config():
        return None
    
    try:
        url = f"{ZENDESK_URL}/api/v2/tickets/{zendesk_ticket_id}.json"
        headers = get_zendesk_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()['ticket']
        
    except requests.RequestException as e:
        print(f"❌ Error fetching ZenDesk ticket {zendesk_ticket_id}: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error fetching ZenDesk ticket: {str(e)}")
        return None

def get_zendesk_ticket_assignee(zendesk_ticket_id: int) -> Optional[Dict]:
    """
    Get assignee information from ZenDesk ticket
    
    Args:
        zendesk_ticket_id (int): The ZenDesk ticket ID
        
    Returns:
        Dict: Assignee information with keys: id, name, email
    """
    ticket_data = get_zendesk_ticket_details(zendesk_ticket_id)
    if not ticket_data:
        return None
    
    assignee_id = ticket_data.get('assignee_id')
    if not assignee_id:
        print(f"⚠️  No assignee found for ZenDesk ticket {zendesk_ticket_id}")
        return None
    
    return get_zendesk_user(assignee_id)

def get_zendesk_user(user_id: int) -> Optional[Dict]:
    """
    Get user information from ZenDesk
    
    Args:
        user_id (int): The ZenDesk user ID
        
    Returns:
        Dict: User information with keys: id, name, email, role
    """
    if not validate_zendesk_config():
        return None
    
    try:
        url = f"{ZENDESK_URL}/api/v2/users/{user_id}.json"
        headers = get_zendesk_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        user_data = response.json()['user']
        return {
            'id': user_data.get('id'),
            'name': user_data.get('name', 'Unknown'),
            'email': user_data.get('email', ''),
            'role': user_data.get('role', 'unknown')
        }
        
    except requests.RequestException as e:
        print(f"❌ Error fetching ZenDesk user {user_id}: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error fetching ZenDesk user: {str(e)}")
        return None

def post_zendesk_comment(zendesk_ticket_id: int, 
                        comment_body: str, 
                        public: bool = False,
                        author_id: Optional[int] = None) -> bool:
    """
    Post a comment to a ZenDesk ticket
    
    Args:
        zendesk_ticket_id (int): The ZenDesk ticket ID
        comment_body (str): The comment text
        public (bool): Whether the comment should be public (default: False for internal)
        author_id (Optional[int]): ID of the comment author
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not validate_zendesk_config():
        return False
    
    try:
        url = f"{ZENDESK_URL}/api/v2/tickets/{zendesk_ticket_id}.json"
        headers = get_zendesk_headers()
        
        # Prepare comment data
        comment_data = {
            'ticket': {
                'comment': {
                    'body': comment_body,
                    'public': public
                }
            }
        }
        
        # Add author if provided
        if author_id:
            comment_data['ticket']['comment']['author_id'] = author_id
        
        response = requests.put(url, headers=headers, json=comment_data, timeout=10)
        response.raise_for_status()
        
        print(f"✅ Successfully posted comment to ZenDesk ticket {zendesk_ticket_id}")
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error posting comment to ZenDesk ticket {zendesk_ticket_id}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error posting comment: {str(e)}")
        return False



def get_zendesk_id_from_ticket(ticket_id: int) -> Optional[int]:
    """
    Get ZenDesk ticket ID from internal ticket ID
    
    Args:
        ticket_id (int): Internal ticket ID
        
    Returns:
        Optional[int]: ZenDesk ticket ID or None if not found
    """
    query = """
        SELECT zendesk_id 
        FROM tickets_ticket 
        WHERE id = %s
    """
    
    try:
        result = execute_query(query, (ticket_id,), fetch_one=True)
        return result['zendesk_id'] if result and result['zendesk_id'] else None
    except Exception as e:
        print(f"❌ Error fetching ZenDesk ID for ticket {ticket_id}: {str(e)}")
        return None



def get_zendesk_ticket_comments(zendesk_ticket_id: int) -> List[Dict]:
    """
    Get all comments for a ZenDesk ticket
    
    Args:
        zendesk_ticket_id (int): The ZenDesk ticket ID
        
    Returns:
        List[Dict]: List of comments with author, body, created_at, etc.
    """
    if not validate_zendesk_config():
        return []
    
    try:
        url = f"{ZENDESK_URL}/api/v2/tickets/{zendesk_ticket_id}/comments.json"
        headers = get_zendesk_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        return response.json()['comments']
        
    except requests.RequestException as e:
        print(f"❌ Error fetching ZenDesk comments for ticket {zendesk_ticket_id}: {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error fetching comments: {str(e)}")
        return []

def test_zendesk_connection() -> bool:
    """
    Test ZenDesk API connection and authentication
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    if not validate_zendesk_config():
        return False
    
    try:
        url = f"{ZENDESK_URL}/api/v2/tickets.json?page[size]=1"
        headers = get_zendesk_headers()
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print("✅ ZenDesk API connection successful!")
        return True
        
    except requests.RequestException as e:
        print(f"❌ ZenDesk API connection failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error testing ZenDesk connection: {str(e)}")
        return False

# Example usage and testing
if __name__ == "__main__":
    print("🔧 ZenDesk Utils Test")
    print("="*50)
    
    # Test connection
    if test_zendesk_connection():
        print("✅ ZenDesk configuration is working!")
        
        # Example: Test with a ticket ID
        test_zendesk_ticket_id = 123  # Replace with actual ZenDesk ticket ID
        
        print(f"\n📋 Testing with ZenDesk ticket {test_zendesk_ticket_id}:")
        
        # Get ticket details
        ticket_details = get_zendesk_ticket_details(test_zendesk_ticket_id)
        if ticket_details:
            print(f"  Subject: {ticket_details.get('subject', 'N/A')}")
            print(f"  Status: {ticket_details.get('status', 'N/A')}")
        
        # Get assignee
        assignee = get_zendesk_ticket_assignee(test_zendesk_ticket_id)
        if assignee:
            print(f"  Assignee: {assignee['name']} ({assignee['email']})")
    else:
        print("❌ ZenDesk configuration needs to be set up!")
        print("Add the following to your .env file:")
        print("ZENDESK_URL=https://yourcompany.zendesk.com")
        print("ZENDESK_EMAIL=your-email@company.com")
        print("ZENDESK_TOKEN=your_api_token_here") 