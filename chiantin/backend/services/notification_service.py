"""Notification service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from typing import List, Optional

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
            metadata=metadata or {},
            reply_count=1
        )
        
        notif_dict = notification.model_dump(by_alias=True)
        await self.db.notifications.insert_one(notif_dict)
        
        return notification
    
    async def create_or_update_support_reply_notification(
        self,
        user_id: str,
        ticket_id: str,
        ticket_subject: str,
        action_url: str = "/support"
    ) -> Notification:
        """
        Create or update a support ticket reply notification.
        Groups multiple replies to the same ticket into a single notification.
        
        If an unread notification exists for this ticket, increments the reply_count.
        Otherwise creates a new notification.
        """
        # Check for existing unread notification for this ticket
        existing = await self.db.notifications.find_one({
            "user_id": user_id,
            "notification_type": "SUPPORT",
            "metadata.ticket_id": ticket_id,
            "metadata.is_reply": True,
            "read": False
        })
        
        now = datetime.now(timezone.utc)
        
        if existing:
            # Update existing notification - increment counter and update timestamp
            new_count = existing.get("reply_count", 1) + 1
            
            # Build the message with count
            if new_count == 1:
                new_message = f"Support has replied to your ticket: {ticket_subject}"
            else:
                new_message = f"New replies on your ticket: {ticket_subject} ({new_count} new messages)"
            
            await self.db.notifications.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "reply_count": new_count,
                        "message": new_message,
                        "created_at": now,  # Update timestamp to latest
                        "title": "New Replies on Your Ticket" if new_count > 1 else "New Reply on Your Ticket"
                    }
                }
            )
            
            # Return the updated notification
            updated_doc = await self.db.notifications.find_one({"_id": existing["_id"]})
            return Notification(**serialize_doc(updated_doc))
        else:
            # Create new notification
            notification = Notification(
                user_id=user_id,
                notification_type=NotificationType.SUPPORT,
                title="New Reply on Your Ticket",
                message=f"Support has replied to your ticket: {ticket_subject}",
                action_url=action_url,
                metadata={
                    "ticket_id": ticket_id,
                    "is_reply": True
                },
                reply_count=1
            )
            
            notif_dict = notification.model_dump(by_alias=True)
            notif_dict["created_at"] = now
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
                if "reply_count" not in serialized:
                    serialized["reply_count"] = 1  # Default for older notifications
                
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
                    "read_at": datetime.now(timezone.utc)
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
                    "read_at": datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count