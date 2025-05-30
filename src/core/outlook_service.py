from src.core.email_service import EmailService
import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from src.utils.logger import logger

class OutlookService(EmailService):
    """Handles Microsoft Graph API authentication and service for Outlook using ROPC flow."""

    TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self):
        self.client_id = os.getenv('OUTLOOK_CLIENT_ID')
        self.username = os.getenv('OUTLOOK_USERNAME')
        self.password = os.getenv('OUTLOOK_PASSWORD')
        self.scope = "https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Mail.Send https://graph.microsoft.com/Mail.ReadWrite"
        self.access_token = None
        self._get_token()

    def _get_token(self):
        data = {
            'client_id': self.client_id,
            'scope': self.scope,
            'username': self.username,
            'password': self.password,
            'grant_type': 'password',
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(self.TOKEN_URL, data=data, headers=headers)
        if response.status_code == 200:
            self.access_token = response.json().get('access_token')
            logger.info("Successfully obtained access token for Outlook.")
        else:
            logger.error(f"Failed to obtain access token: {response.text}")
            raise Exception(f"Failed to obtain access token: {response.text}")

    def _headers(self):
        if not self.access_token:
            self._get_token()
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def send_message(self, to: str, subject: str, body: str, cc: Optional[list] = None, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
        user_id = self.username
        endpoint = f"{self.GRAPH_API_BASE}/users/{user_id}/sendMail"
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "toRecipients": [
                    {"emailAddress": {"address": to}}
                ]
            }
        }
        if cc:
            message["message"]["ccRecipients"] = [
                {"emailAddress": {"address": email}} for email in cc
            ]
        try:
            response = requests.post(endpoint, headers=self._headers(), data=json.dumps(message))
            response.raise_for_status()
            logger.info(f"Email sent successfully to {to}")
            return True
        except Exception as e:
            logger.error(f"Error sending email to {to}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.content}")
            return False

    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        user_id = self.username
        endpoint = f"{self.GRAPH_API_BASE}/users/{user_id}/messages"
        params = {
            "$filter": f"conversationId eq '{thread_id}'",
            "$orderby": "receivedDateTime asc"
        }
        try:
            response = requests.get(endpoint, headers=self._headers(), params=params)
            response.raise_for_status()
            messages = response.json().get("value", [])
            normalized = []
            for msg in messages:
                normalized.append({
                    'message_id': msg.get('id'),
                    'thread_id': msg.get('conversationId'),
                    'subject': msg.get('subject', ''),
                    'body': msg.get('body', {}).get('content', ''),
                    'from': msg.get('from', {}).get('emailAddress', {}).get('address', ''),
                    'date': msg.get('receivedDateTime', ''),
                })
            return normalized
        except Exception as e:
            logger.error(f"Error fetching thread messages: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.content}")
            return []

    def reply_to_message(self, message_id: str, body: str, html_content: bool = True) -> bool:
        user_id = self.username
        endpoint = f"{self.GRAPH_API_BASE}/users/{user_id}/messages/{message_id}/reply"
        reply = {
            "message": {
                "body": {
                    "contentType": "HTML" if html_content else "Text",
                    "content": body
                }
            }
        }
        try:
            response = requests.post(endpoint, headers=self._headers(), data=json.dumps(reply))
            response.raise_for_status()
            logger.info(f"Reply sent successfully to message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending reply to message {message_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.content}")
            return False

    def list_messages(self, top=10, filter_query=None):
        logger.debug(f"[list_messages] Called with top={top}, filter_query={filter_query}")
        try:
            user_id = os.getenv("OUTLOOK_USER_ID")
            logger.debug(f"[list_messages] OUTLOOK_USER_ID: {user_id}")
            try:
                endpoint = f"/users/{user_id}/messages"
                logger.debug(f"[list_messages] Endpoint: {endpoint}")
                query_params = {
                    "$top": str(top),
                    "$orderby": "receivedDateTime desc"
                }
                if filter_query:
                    query_params["$filter"] = str(filter_query)
                logger.debug(f"[list_messages] Query params: {query_params}")
                query_string = urlencode(query_params)
                url = f"{endpoint}?{query_string}"
                logger.debug(f"[list_messages] Full URL: {url}")
            except Exception as param_err:
                logger.error(f"[list_messages] Error constructing parameters: {param_err}")
                raise
            response = self.service.get(url)
            response.raise_for_status()
            return response.json().get("value", [])
        except Exception as e:
            logger.error(f"[list_messages] Error listing messages: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[list_messages] Response content: {e.response.content}")
            raise
            
    def get_message(self, message_id):
        logger.debug(f"[get_message] Called with message_id={message_id}")
        try:
            user_id = os.getenv("OUTLOOK_USER_ID")
            logger.debug(f"[get_message] OUTLOOK_USER_ID: {user_id}")
            try:
                endpoint = f"/users/{user_id}/messages/{message_id}"
                logger.debug(f"[get_message] Endpoint: {endpoint}")
            except Exception as param_err:
                logger.error(f"[get_message] Error constructing endpoint: {param_err}")
                raise
            response = self.service.get(endpoint)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[get_message] Error getting message {message_id}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"[get_message] Response content: {e.response.content}")
            raise 