# HelpDesk Multi-Agent System

A sophisticated multi-agent system for automated email processing and helpdesk management, powered by AI.

## 🚀 Features

- **Smart Email Monitoring**
  - Real-time Gmail inbox monitoring
  - Configurable email filtering
  - Automated email processing pipeline

- **AI-Powered Classification**
  - Intelligent email categorization (Demande/Incident)
  - Natural Language Processing for content analysis
  - Confidence scoring and evidence extraction

- **Advanced User Information Extraction**
  - Automatic extraction of user details from emails
  - Inference of missing information from context
  - Creation of structured user profiles

- **Intelligent Ticket Management**
  - Automated ticket creation and categorization
  - Subcategory classification with confidence scoring
  - Priority determination based on content analysis
  - Persistent ticket storage and retrieval

- **Follow-Up System**
  - Automatic detection of missing information
  - AI-generated personalized follow-up emails
  - Smart handling of incomplete ticket data

- **Email Communication**
  - Automated response generation
  - Personalized email templates
  - Secure Gmail API integration
  - Professional formatting and structuring

- **Multi-Agent Architecture**
  - Collaborative agent system
  - Specialized agents for different tasks (Classification, Incident, Demande)
  - Dynamic workflow management
  - State tracking between processing steps

## 📋 Prerequisites

- Python 3.8+
- Gmail API credentials
- Groq API key
- Required Python packages (see requirements.txt)

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/HelpDesk_Multi_Agent_System.git
   cd HelpDesk_Multi_Agent_System
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   - Place your Gmail API `credentials.json` in `config/credentials/`
   - Create `groq_api_key.txt` with your LLM API key in the same folder

## ⚙️ Configuration

Edit `config/settings.py` to customize system behavior:

```python
# Email monitoring
POLL_INTERVAL_SECONDS = 10  # Check for new emails every 10 seconds
SPECIFIC_EMAIL = "example@gmail.com"  # Monitor specific email address

# LLM Settings
LLM_MODEL_NAME = "qwen-2.5-32b"  # Groq model name
LLM_TEMPERATURE = 0.1  # Model temperature for response generation
```

## 🚀 Usage

1. **Start the system**
   ```bash
   python -m src.main
   ```

2. **System Workflow**
   - Authenticates with Gmail using OAuth 2.0
   - Monitors specified inbox for new emails
   - Classifies emails as Incidents or Demandes
   - Extracts user information and ticket details
   - Creates appropriate tickets in the management system
   - Sends follow-up emails for missing information
   - Logs all activities and results

## 🔧 Agent Descriptions

The system uses several specialized agents, each with a specific role:

- **ClassificationAgent**: Determines whether an email is an incident or a service request
- **IncidentAgent**: Processes technical issues, classifies into subcategories, creates tickets
- **DemandeAgent**: Handles service requests and information inquiries
- **UserInfoExtractor**: Extracts and structures user information from emails
- **FollowUpManager**: Identifies missing information and generates follow-up emails

## 📊 System Architecture

```
HelpDesk_Multi_Agent_System/
├── config/
│   ├── credentials/
│   └── settings.py
├── src/
│   ├── agents/
│   │   ├── classification_agent.py
│   │   ├── demande_agent.py
│   │   ├── incident_agent.py
│   │   ├── follow_up_manager.py
│   │   └── user_info_extractor.py
│   ├── core/
│   │   ├── gmail_service.py
│   │   ├── gmail_sender.py
│   │   ├── llm_handler.py
│   │   ├── ticket_management.py
│   │   └── workflow.py
│   ├── monitoring/
│   │   └── gmail_monitor.py
│   ├── utils/
│   │   ├── logger.py
│   │   └── prompts.py
│   └── main.py
├── requirements.txt
└── README.md
```

## 🔍 Monitoring and Logging

- Comprehensive logging system with debug levels
- Real-time activity monitoring
- Detailed error tracking and debugging
- Email sending transaction logs
- Performance metrics collection

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
