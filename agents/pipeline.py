from textblob import TextBlob

class EmailProcessingAgent:
    def run(self, ticket: dict) -> dict:
        ticket['subject'] = ticket.get('subject', '').strip()
        ticket['description'] = ticket.get('description', '').strip()
        tb = TextBlob(ticket['description'])
        ticket['sentiment'] = (
            'positive' if tb.sentiment.polarity > 0.1 else
            'negative' if tb.sentiment.polarity < -0.1 else
            'neutral'
        )
        return ticket

class CategorizationAgent:
    def run(self, ticket: dict) -> dict:
        desc = ticket.get('description', '').lower()
        if "error" in desc or "crash" in desc or "fail" in desc:
            ticket['category'] = "Bug"
        elif "feature" in desc or "request" in desc:
            ticket['category'] = "Feature Request"
        elif "how to" in desc or "help" in desc or "guide" in desc:
            ticket['category'] = "Education Gap"
        elif "does not support" in desc or "missing" in desc:
            ticket['category'] = "Product Gap"
        else:
            ticket['category'] = "Inquiry"
        return ticket

class PrioritizationAgent:
    def run(self, ticket: dict) -> dict:
        category = ticket.get('category', '')
        sentiment = ticket.get('sentiment', '')
        desc = ticket.get('description', '').lower()
        if category == "Bug":
            ticket['impact'] = "High" if "crash" in desc else "Medium"
            ticket['urgency'] = "Urgent" if sentiment == "negative" else "Normal"
            ticket['ai_priority'] = "P1" if ticket['impact'] == "High" else "P2"
        elif category == "Feature Request":
            ticket['impact'] = "Low"
            ticket['urgency'] = "Normal"
            ticket['ai_priority'] = "P3"
        elif category == "Product Gap":
            ticket['impact'] = "Medium"
            ticket['urgency'] = "Normal"
            ticket['ai_priority'] = "P2"
        else:
            ticket['impact'] = "Low"
            ticket['urgency'] = "Normal"
            ticket['ai_priority'] = "P4"
        return ticket

class ResolutionAgent:
    def run(self, ticket: dict) -> dict:
        category = ticket.get('category', '')
        if category == "Bug":
            ticket['next_action'] = "Escalate to L2/L3"
            ticket['escalation'] = "Yes"
            ticket['troubleshooting_steps'] = "Check logs, reproduce bug, collect environment details."
            ticket['resolution'] = "Bug logged, escalation initiated."
            ticket['counter_questions'] = ""
        elif category == "Feature Request":
            ticket['next_action'] = "Acknowledge, add to roadmap review"
            ticket['escalation'] = "No"
            ticket['troubleshooting_steps'] = "Confirm requested feature, collect use case details."
            ticket['resolution'] = "Thank you for your suggestion. We will review it."
            ticket['counter_questions'] = ""
        elif category == "Education Gap":
            ticket['next_action'] = "Reply with knowledge base article"
            ticket['escalation'] = "No"
            ticket['troubleshooting_steps'] = "Provide user guide links."
            ticket['resolution'] = "Sent step-by-step instructions."
            ticket['counter_questions'] = ""
        elif category == "Product Gap":
            ticket['next_action'] = "Flag to Product Team"
            ticket['escalation'] = "Yes"
            ticket['troubleshooting_steps'] = "Verify gap, collect requirements."
            ticket['resolution'] = "Informed Product Team for review."
            ticket['counter_questions'] = ""
        else:
            ticket['next_action'] = "Ask for more info"
            ticket['escalation'] = "No"
            ticket['troubleshooting_steps'] = "Request additional details."
            ticket['resolution'] = ""
            ticket['counter_questions'] = "Could you provide more details on your request?"
        return ticket

class FeedbackAgent:
    def run(self, ticket: dict) -> dict:
        ticket['feedback'] = "Pending"
        return ticket

def agent_pipeline(ticket: dict) -> dict:
    for Agent in [
        EmailProcessingAgent,
        CategorizationAgent,
        PrioritizationAgent,
        ResolutionAgent,
        FeedbackAgent,
    ]:
        ticket = Agent().run(ticket)
    return ticket
