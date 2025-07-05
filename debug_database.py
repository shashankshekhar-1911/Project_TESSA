import sys
from database_utils import execute_query, test_database_connection, check_table_exists, get_table_info

def debug_database_connection():
    """
    Test basic database connectivity
    """
    print("🔍 STEP 1: Testing Database Connection")
    print("="*50)
    
    if test_database_connection():
        print("✅ Database connection successful!")
        return True
    else:
        print("❌ Database connection failed!")
        print("Check your environment variables:")
        print("  - POSTGRES_DB")
        print("  - POSTGRES_USER") 
        print("  - POSTGRES_PASSWORD")
        print("  - POSTGRES_HOST")
        print("  - POSTGRES_PORT")
        return False

def debug_table_structure():
    """
    Check if the tickets_ticket table exists and its structure
    """
    print("\n🔍 STEP 2: Checking Table Structure")
    print("="*50)
    
    # Check if table exists
    if check_table_exists('tickets_ticket'):
        print("✅ Table 'tickets_ticket' exists!")
        
        # Get table info
        columns = get_table_info('tickets_ticket')
        if columns:
            print(f"\n📋 Table columns ({len(columns)}):")
            for col in columns:
                print(f"  - {col['column_name']} ({col['data_type']})")
        return True
    else:
        print("❌ Table 'tickets_ticket' does not exist!")
        print("Available tables:")
        
        # Try to list some common table variations
        possible_tables = ['ticket', 'tickets', 'Ticket', 'Tickets']
        for table_name in possible_tables:
            if check_table_exists(table_name):
                print(f"  ✅ Found: {table_name}")
        return False

def debug_ticket_search(ticket_id: int):
    """
    Debug ticket search with various approaches
    """
    print(f"\n🔍 STEP 3: Searching for Ticket ID {ticket_id}")
    print("="*50)
    
    # Try different approaches to find the ticket
    
    # 1. Basic search
    print("📍 Approach 1: Basic ID search")
    query1 = "SELECT id, description, support_theme FROM tickets_ticket WHERE id = %s"
    result1 = execute_query(query1, (ticket_id,), fetch_one=True)
    if result1:
        print(f"✅ Found ticket: {result1}")
        return result1
    else:
        print(f"❌ No ticket found with ID {ticket_id}")
    
    # 2. Search with CAST (in case ID is stored as text)
    print("\n📍 Approach 2: Searching with ID as text")
    query2 = "SELECT id, description, support_theme FROM tickets_ticket WHERE id::text = %s"
    result2 = execute_query(query2, (str(ticket_id),), fetch_one=True)
    if result2:
        print(f"✅ Found ticket (ID as text): {result2}")
        return result2
    else:
        print(f"❌ No ticket found with ID as text {ticket_id}")
    
    # 3. Check what IDs actually exist (first 10)
    print("\n📍 Approach 3: Checking existing ticket IDs")
    query3 = "SELECT id FROM tickets_ticket ORDER BY id LIMIT 10"
    existing_ids = execute_query(query3)
    if existing_ids:
        print("✅ Found these ticket IDs:")
        for row in existing_ids:
            print(f"  - ID: {row['id']}")
        
        # Check if any are close to our target
        target_ids = [row['id'] for row in existing_ids]
        if target_ids:
            print(f"\n💡 Try one of these existing IDs instead of {ticket_id}")
    else:
        print("❌ No tickets found in the table at all!")
    
    # 4. Check total count
    print("\n📍 Approach 4: Checking total ticket count")
    query4 = "SELECT COUNT(*) as total FROM tickets_ticket"
    count_result = execute_query(query4, fetch_one=True)
    if count_result:
        total = count_result['total']
        print(f"📊 Total tickets in database: {total}")
        if total == 0:
            print("❌ The tickets_ticket table is empty!")
    
    return None

def debug_column_names():
    """
    Check if the column names we're using are correct
    """
    print("\n🔍 STEP 4: Checking Column Names")
    print("="*50)
    
    # Get actual column names
    columns = get_table_info('tickets_ticket')
    if columns:
        column_names = [col['column_name'] for col in columns]
        
        # Check if our expected columns exist
        expected_columns = ['id', 'description', 'support_theme']
        
        print("🔍 Checking expected columns:")
        for col in expected_columns:
            if col in column_names:
                print(f"  ✅ '{col}' exists")
            else:
                print(f"  ❌ '{col}' NOT FOUND")
                # Suggest similar columns
                similar = [c for c in column_names if col.lower() in c.lower() or c.lower() in col.lower()]
                if similar:
                    print(f"      💡 Similar columns: {similar}")
        
        print(f"\n📋 All available columns: {column_names}")
    else:
        print("❌ Could not get column information")

def main():
    """
    Run complete database debugging
    """
    if len(sys.argv) < 2:
        print("Usage: python debug_database.py <ticket_id>")
        print("Example: python debug_database.py 925")
        return
    
    try:
        ticket_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Error: '{sys.argv[1]}' is not a valid ticket ID")
        return
    
    print("🔧 DATABASE DEBUGGING TOOL")
    print("="*50)
    
    # Step 1: Test connection
    if not debug_database_connection():
        return
    
    # Step 2: Check table structure
    if not debug_table_structure():
        return
    
    # Step 3: Debug ticket search
    debug_ticket_search(ticket_id)
    
    # Step 4: Check column names
    debug_column_names()
    
    print("\n🎯 DEBUGGING COMPLETE")
    print("="*50)
    print("If you found the issue, update your code accordingly!")

if __name__ == "__main__":
    main() 