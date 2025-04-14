# Helpdesk Multi-Agent System

## Features

- Gmail inbox monitoring
- AI-powered email classification (Demande/Incident)
- Customizable processing workflow
- Persistent vector storage for RAG (Retrieval-Augmented Generation)
- Multi-agent collaboration

## Project Structure

HelpDesk_Multi_Agent_System/
├── config/ # Configuration files
│ ├── init.py
│ ├── settings.py # Application settings
│ └── credentials/ # Authentication files
│ ├── credentials.json # Gmail API credentials
│ ├── token.json # Gmail auth token
│ └── groq_api_key.txt # LLM API key
│
├── src/ # Main application code
│ ├── core/ # Core system components
│ │ ├── gmail_service.py # Gmail API wrapper
│ │ ├── llm_handler.py # LLM interface
│ │ ├── email_processor.py # Email classification
│ │ └── workflow.py # Processing workflow
│ │
│ ├── monitoring/ # Email monitoring
│ │ └── gmail_monitor.py # Inbox monitoring
│ │
│ ├── utils/ # Utilities
│ │ ├── logger.py # Logging setup
│ │ ├── prompts.py # LLM prompts
│ │ └── document_parser.py # File processing
│ │
│ └── main.py # Entry point
├── requirements.txt # Python dependencies
└── README.md # This file


## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/HelpDesk_Multi_Agent_System.git
   cd HelpDesk_Multi_Agent_System
   ```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up credentials:

Place your Gmail API credentials.json in config/credentials/

Create groq_api_key.txt with your LLM API key in the same folder

## Configuration
Edit **config/settings.py** to customize:

```python
# Email monitoring
POLL_INTERVAL_SECONDS = 60  # Check for new emails every 60 seconds
AUTHORIZED_EMAILS = ["helpdesk@yourcompany.com"]  # Allowed senders

# LLM Settings
LLM_MODEL_NAME = "qwen-2.5-32b"
LLM_TEMPERATURE = 0.1
```

## Usage

Run the system:

```bash
python -m src.main
```

The system will:

1. **Authenticate with Gmail**  
   - OAuth 2.0 authentication flow  
   - Token generation and storage  

2. **Start monitoring the inbox**  
   - Continuous polling at configured intervals  
   - New email detection  

3. **Process new emails using the workflow**  
   - Extract email content and metadata  
   - Pass through classification pipeline  

4. **Classify emails (Demande/Incident)**  
   - LLM-powered categorization  
   - Confidence scoring and evidence extraction  

5. **Log all actions**  
   - Timestamped activity logging  
   - Error tracking and debugging  

## Workflow Customization
Edit **src/core/workflow.py** to modify the processing pipeline. Example nodes:

```python
Copy
workflow.add_node("classify_email", email_processor.classify_email)
workflow.add_node("escalate_urgent", escalate_to_support_team)
workflow.add_node("send_acknowledgment", send_confirmation_email)
```
##Contributing


### Checklist Version
```markdown
- [ ] Fork the repository  
- [ ] Create feature branch (`git checkout -b feature/fooBar`)  
- [ ] Commit your changes (`git commit -m 'Add fooBar'`)  
- [ ] Push to the branch (`git push origin feature/fooBar`)  
- [ ] Create new Pull Request
