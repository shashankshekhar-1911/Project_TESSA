import pandas as pd
import pprint
import sys
import os

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.request_processor import process_ticket

# Add the parent directory to the Python path
# from main import index

# Read the Excel files
ticket_data = pd.read_excel("/Users/ishan.prakash/Documents/TESSA/tessa_backend/zendesk_data/zendesk_tickets_processed_v2.xlsx")
user_data = pd.read_excel("/Users/ishan.prakash/Documents/TESSA/tessa_backend/zendesk_data/zendesk_users.xlsx")
organization_data = pd.read_excel("/Users/ishan.prakash/Documents/TESSA/tessa_backend/zendesk_data/zendesk_organizations.xlsx")
comments_data = pd.read_excel("/Users/ishan.prakash/Documents/TESSA/tessa_backend/zendesk_data/zendesk_comments.xlsx")

# Create a copy of the dataframe
processed_tickets = ticket_data.copy()

# Define the columns to be populated
columns_to_populate = [
    'priority',
    'organization_id',
    'product',
    'support_theme',
    'summary',
    'severity',
    'ticket_type',
    'interface_affected',
    'code_change',
    'module',
    'workaround',
    'effort_aidash',
    'urgency'
]

# Process each ticket
for index, row in ticket_data.iterrows():
    ticket_id = row['ticket_id']
    print(f"\nProcessing ticket {ticket_id} ({index + 1}/{len(ticket_data)})")
    
    # Get empty fields for this ticket
    empty_fields = [col for col in columns_to_populate if pd.isna(row[col])]
    
    if not empty_fields:
        print(f"No empty fields for ticket {ticket_id}, skipping...")
        continue
        
    print(f"Empty fields to process: {empty_fields}")
    
    # Get the first comment for this ticket
    comments = comments_data[comments_data['ticket_id'] == ticket_id]
    if not comments.empty:
        comment_start = comments.iloc[0].to_dict()
        
        try:
            # Process the ticket
            ticket_summary = process_ticket(comment_start)
            
            # Update only the empty fields in processed_tickets
            for column in empty_fields:
                if column in ticket_summary and ticket_summary[column] is not None:
                    # Extract the value from the nested dictionary
                    value = ticket_summary[column].get('value', None)
                    if value is not None:
                        processed_tickets.at[index, column] = value
                        print(f"Updated {column}: {value}")
            
        except Exception as e:
            print(f"Error processing ticket {ticket_id}: {str(e)}")
            continue
    else:
        print(f"No comments found for ticket {ticket_id}")

# Save the processed tickets to a new Excel file
output_path = "/Users/ishan.prakash/Documents/TESSA/tessa_backend/zendesk_data/zendesk_tickets_processed_updated.xlsx"
processed_tickets.to_excel(output_path, index=False)
print(f"\nProcessed tickets saved to: {output_path}")

# Print summary of updates
print("\nSummary of updates:")
for column in columns_to_populate:
    original_empty = ticket_data[column].isna().sum()
    new_empty = processed_tickets[column].isna().sum()
    filled = original_empty - new_empty
    print(f"{column}: {filled} values filled, {new_empty} still empty")




