#Loading global modules
import os
from dotenv import load_dotenv
load_dotenv()


#Loading local modules
import email_parser
import email_translator
import jira_creator

#Apply sanity env checks
if "GROQ_API_KEY" not in os.environ:
    raise ValueError("GROQ_API_KEY is not set in the environment")


# Parse the email
eml_file_path = os.path.join(os.path.dirname(__file__),'client_email.eml')
email_metadata = email_parser.extract_email_metadata(eml_file_path)


# Understand the email
email_context = email_translator.decode_client_email(email_metadata)
print(email_context)
# Create the ticket
#jira_fields = jira_creator.jira_fields(email_context)
#jira_creator.create_ticket(jira_fields)