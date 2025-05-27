# Configuration Setup Guide

This directory contains template configuration files for the HelpDesk Multi-Agent System. Follow these steps to set up your configuration:

## 1. Create the Configuration Directory

```bash
mkdir -p config/credentials
```

## 2. Copy Template Files

Copy all files from this template directory to your `config` directory, removing the `.template` extension:

```bash
cp config.template/settings.py.template config/settings.py
cp config.template/credentials/credentials.json.template config/credentials/credentials.json
cp config.template/credentials/groq_api_key.txt.template config/credentials/groq_api_key.txt
```

## 3. Configure Your Settings

### Gmail API Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials
5. Download the credentials and save them as `config/credentials/credentials.json`
6. Update `AUTHORIZED_EMAILS` in `settings.py` with your email address

### Groq API Setup
1. Go to [Groq Console](https://console.groq.com/)
2. Create an account and get your API key
3. Save your API key in `config/credentials/groq_api_key.txt`

## 4. Update Settings

Edit `config/settings.py` and update the following:
- `DEBUG_MODE`: Set to `False` in production
- `AUTHORIZED_EMAILS`: Add your authorized email addresses
- `LLM_MODEL_NAME`: Update with your preferred model
- Other settings as needed

## Security Notes
- Never commit your actual credentials to the repository
- Keep your API keys and credentials secure
- The `config` directory is already in `.gitignore`

## Troubleshooting
If you encounter any issues:
1. Check that all files are in the correct locations
2. Verify that your API keys and credentials are valid
3. Ensure the file permissions are correct
4. Check the logs for any error messages 