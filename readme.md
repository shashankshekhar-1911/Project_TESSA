***What does the Agent V1 intend to do?***
1. Reads the incoming email request
2. Understands the email and extracts relevant metadata for the request
3. Files the relevant ticket in Jira
4. Creates an initial response for the L1 human support to send to the client. This could either be just an acknowledge or counter questions to understand the ask better.
5. If the request requires technical support, creates a ticket for L2 support team


***Notes***
Rename the .env.example file to .env before using