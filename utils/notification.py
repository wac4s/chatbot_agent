# Create Notification Utility Function
from app.models import Notification
from sqlalchemy.orm import Session

def create_notification(db: Session, recipient_id: int, message: str):
    note = Notification(recipient_id=recipient_id, message=message)
    db.add(note)
    db.commit()

# Add helper to create notifications
# app/utils/notifications.py
from app.models import Notification
from datetime import datetime

def create_notification(db, recipient_id, sender_id, message):
    notif = Notification(
        recipient_id=recipient_id,
        sender_id=sender_id,
        message=message,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
