#Converts an email in a .eml format to a JSON object capturing key details

import os
import json
import datetime
import email
from email import policy
from email.parser import BytesParser
from eml_parser import EmlParser

def json_serial(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def extract_email_metadata(eml_file_path):
    with open(eml_file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

    # Extract subject
    subject = msg['subject']

    # Extract To and CC fields
    to_addresses = msg.get_all('to', [])
    cc_addresses = msg.get_all('cc', [])

    # Parse names and email addresses
    to_parsed = email.utils.getaddresses(to_addresses)
    cc_parsed = email.utils.getaddresses(cc_addresses)

    # Extract email body
    if msg.is_multipart():
        for part in msg.iter_parts():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
    else:
        body = msg.get_content()


    email_metadata = {
        "subject": subject,
        "to": to_parsed,
        "cc": cc_parsed,
        "body": body
    }
    return json.loads(json.dumps(email_metadata, default=json_serial, indent=2))