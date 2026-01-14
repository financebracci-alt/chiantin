"""Notification service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import List

from schemas.notifications import Notification, NotificationType
from utils.common import serialize_doc


class NotificationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        action_url: str = None,
        metadata: dict = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            metadata=metadata or {}
        )
        
        notif_dict = notification.model_dump(by_alias=True)
        await self.db.notifications.insert_one(notif_dict)
        
        return notification
    
    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = {"user_id": user_id}
        if unread_only:
            query["read"] = False
        
        cursor = self.db.notifications.find(query).sort("created_at", -1).limit(limit)
        notifications = []
        async for doc in cursor:
            try:
                # Ensure required fields exist with defaults
                serialized = serialize_doc(doc)
                if "notification_type" not in serialized or serialized["notification_type"] is None:
                    serialized["notification_type"] = "ACCOUNT"  # Default type
                if "message" not in serialized:
                    serialized["message"] = serialized.get("title", "Notification")
                if "read" not in serialized:
                    serialized["read"] = serialized.get("is_read", False)
                
                notifications.append(Notification(**serialized))
            except Exception as e:
                # Skip malformed notifications but log the error
                print(f"Warning: Skipping malformed notification {doc.get('_id')}: {e}")
                continue
        
        return notifications
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read."""
        result = await self.db.notifications.update_one(
            {"_id": notification_id, "user_id": user_id},
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.notifications.update_many(
            {"user_id": user_id, "read": False},
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count