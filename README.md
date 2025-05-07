# HelpDesk Multi-Agent System

A sophisticated multi-agent system for automated email processing and helpdesk management, powered by AI.

## 🚀 Features

- **Smart Email Monitoring**
  - Real-time Gmail inbox monitoring
  - Configurable email filtering
  - Automated email processing pipeline
  - Intelligent tracking of email threads and responses

- **AI-Powered Classification**
  - Intelligent email categorization (Demande/Incident)
  - Natural Language Processing for content analysis
  - Confidence scoring and evidence extraction

- **Advanced Information Extraction Pipeline**
  - Field extraction from email content
  - Contextual subcategory extraction with rules
  - Priority detection based on content analysis
  - Progress tracking at each extraction stage

- **Structured Ticket Management**
  - Sequential ticket numbering system (TKT-YYYYMMDD-XXXX format)
  - Atomic file operations for reliable ticket storage
  - Temporary ticket saving during processing stages
  - Thread-based ticket tracking and linking
  - Persistent storage with consistent organization

- **Comprehensive Follow-Up System**
  - Specialized follow-up agents for different missing information types
  - User response monitoring and state tracking
  - Smart thread management for ongoing conversations
  - Automatic state updates based on user responses

- **Email Communication**
  - Automated response generation
  - Personalized email templates
  - Secure Gmail API integration
  - Professional formatting and structuring

- **Multi-Agent Architecture**
  - Task-specific agent specialization
  - Improved separation of concerns
  - Stateful workflow management
  - Process stage tracking with clear handoffs

- **Real-time Dashboard**
  - Interactive ticket visualization and filtering
  - Dynamic date range selection
  - Status-based categorization
  - Multi-format ticket data compatibility
  - User-friendly interface for system monitoring

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
   - Processes through multi-stage extraction pipeline:
     - Field extraction (user details, request info)
     - Subcategory extraction with rules-based validation
     - Priority detection with contextual analysis
   - Creates tickets with appropriate status tracking
   - Sends follow-up emails for missing information
   - Monitors for user responses and updates ticket accordingly
   - Logs all activities and results

## 🔧 Agent Architecture

The system uses specialized agents, each handling a specific aspect of the workflow:

- **ClassificationAgent**: Determines whether an email is an incident or a service request
- **TicketCreationAgent**: Creates initial ticket structure from email content
- **FieldExtractionAgent**: Extracts essential information fields from email content
- **SubcategoryExtractionAgent**: Identifies appropriate subcategory for the ticket
- **PriorityDetectionAgent**: Analyzes content to determine appropriate priority level
- **ResponseMonitors**: Track user replies to follow-up emails
  - **UserResponseMonitor**: Processes general user responses
  - **SubcategoryResponseMonitor**: Handles subcategory confirmation responses
- **Follow-Up Agents**: Generate specialized follow-up emails for missing information
  - **MissingFieldsFollowUpAgent**: Follows up on incomplete basic information
  - **MissingSubcategoryFollowUpAgent**: Requests clarification on ticket category
  - **PriorityFollowUpAgent**: Seeks clarification on urgency when unclear
  - **ConfirmSubcategoryFollowUpAgent**: Confirms subcategory selection with user

## 📊 System Architecture

```
HelpDesk_Multi_Agent_System/
├── config/
│   ├── credentials/
│   └── settings.py
├── dashboard_data/
│   └── (Dashboard data files)
├── src/
│   ├── agents/
│   │   ├── classification_agent.py
│   │   ├── confirm_subcategory_follow_up_agent.py
│   │   ├── demande_agent.py
│   │   ├── field_extraction_agent.py
│   │   ├── missing_fields_follow_up_agent.py
│   │   ├── missing_subcategory_follow_up_agent.py
│   │   ├── priority_detection_agent.py
│   │   ├── priority_follow_up_agent.py
│   │   ├── subcategory_extraction_agent.py
│   │   ├── subcategory_response_monitor.py
│   │   ├── ticket_creation_agent.py
│   │   └── user_response_monitor.py
│   ├── core/
│   │   ├── config/
│   │   ├── gmail_service.py
│   │   ├── gmail_sender.py
│   │   ├── llm_handler.py
│   │   ├── subcategory_rules.py
│   │   ├── ticket_management.py
│   │   └── workflow.py
│   ├── dashboard/
│   │   └── app.py
│   ├── monitoring/
│   │   └── gmail_monitor.py
│   ├── tickets/
│   │   └── (Ticket management functionality)
│   ├── utils/
│   │   ├── email_utils.py
│   │   ├── logger.py
│   │   └── prompts.py
│   └── main.py
├── tickets/
│   ├── counter.json
│   └── YYYY/MM/DD/
│       └── (Ticket files organized by date)
├── requirements.txt
└── README.md
```

## 🎯 Ticket Handling

### Ticket Creation Workflow
1. **Initial Email Processing**
   - Email content is classified and basic ticket created
   - Thread ID used for tracking and linking related emails

2. **Field Extraction**
   - Temporary ticket saved with extracted fields
   - Status marked as "in-progress"

3. **Subcategory Extraction**
   - Subcategory determined using rules-based system
   - Temporary ticket updated with subcategory information

4. **Priority Detection**
   - Priority level assigned based on content analysis
   - Final ticket created with complete information

### Ticket Naming Convention
- Format: `TKT-YYYYMMDD-XXXX`
- Sequential counter maintained in counter.json
- Temporary tickets use thread_id_TEMP.json naming
- Final tickets use thread_id.json

### Follow-up Process
1. Missing information detected during any extraction stage
2. Appropriate follow-up agent generates specific email
3. Response monitor tracks user replies
4. Ticket updated with new information from responses
5. Processing continues from appropriate stage

## 📊 Dashboard

The dashboard provides a real-time view of the ticket system:
- Interactive filtering by date range, status, and category
- Visual representation of ticket distribution
- Quick search and filtering capabilities
- Detailed ticket information view
- Status tracking and progress visualization

Access the dashboard at `http://localhost:8051` after starting it.

## 🔍 Monitoring and Logging

- Comprehensive logging system with debug levels
- Real-time activity monitoring
- Detailed error tracking and debugging
- Email sending transaction logs
- Performance metrics collection
- Atomic file operations for data integrity
- Thread tracking for complete conversation history

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
