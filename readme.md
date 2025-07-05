# TESSA Support AI Platform (Django Edition)

## Features
- Modular multi-agent pipeline (Email Processing, Categorization, Prioritization, Resolution, Feedback)
- REST API (Django REST Framework)
- Dashboard (Django templates)
- Live Zendesk & Jira integration
- MCP integration (configurable toggle)
- Postgres (native) & MongoDB (via mongoengine)
- Fully dockerized (Docker, Compose)
- Easy extension for LLM/Bedrock/AgenticAI/MCP

## Setup

1. **Clone this repo and copy `.env.example` to `.env`**  
   Fill in your DB, Zendesk, Jira, and MCP credentials as needed.

2. **Build and run:**
   ```sh
   docker-compose up --build
