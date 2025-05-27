from typing import List, Dict, Any, Optional

class EmailService:
    def send_message(self, to: str, subject: str, body: str, cc: Optional[list] = None, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
        raise NotImplementedError

    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def reply_to_message(self, message_id: str, body: str, html_content: bool = True) -> bool:
        raise NotImplementedError 