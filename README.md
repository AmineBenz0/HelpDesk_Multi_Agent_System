# HelpDesk Multi-Agent System

A sophisticated multi-agent system for automated email processing and helpdesk management, powered by AI and machine learning.

## 🚀 Features

- **Smart Email Monitoring**
  - Real-time Gmail inbox monitoring
  - Configurable email filtering
  - Automated email processing pipeline

- **AI-Powered Classification**
  - Intelligent email categorization (Demande/Incident)
  - Natural Language Processing for content analysis
  - Confidence scoring and evidence extraction

- **Multi-Agent Architecture**
  - Collaborative agent system
  - Specialized agents for different tasks
  - Dynamic workflow management

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

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure credentials**
   - Place your Gmail API `credentials.json` in `config/credentials/`
   - Create `groq_api_key.txt` with your LLM API key in the same folder

## ⚙️ Configuration

Edit `config/settings.py` to customize system behavior:

```python
# Email monitoring
POLL_INTERVAL_SECONDS = 60  # Check for new emails every 60 seconds
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
   - Processes emails through the classification pipeline
   - Executes configured workflow actions
   - Logs all activities and results

## 🔧 Workflow Customization

Modify `src/core/workflow.py` to customize the processing pipeline:

```python
workflow.add_node("classify_email", email_processor.classify_email)
workflow.add_node("escalate_urgent", escalate_to_support_team)
workflow.add_node("send_acknowledgment", send_confirmation_email)
```

## 📊 System Architecture

```
HelpDesk_Multi_Agent_System/
├── config/
│   ├── credentials/
│   └── settings.py
├── src/
│   ├── core/
│   ├── monitoring/
│   ├── processing/
│   └── utils/
├── requirements.txt
└── README.md
```

## 🔍 Monitoring and Logging

- Comprehensive logging system
- Real-time activity monitoring
- Error tracking and debugging
- Performance metrics collection

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request