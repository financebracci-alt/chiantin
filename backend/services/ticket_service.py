"""Support ticket service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException

from schemas.tickets import Ticket, TicketCreate, MessageCreate, TicketMessage, TicketStatus
from utils.common import serialize_doc


class TicketService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_ticket(self, user_id: str, user_name: str, data: TicketCreate) -> Ticket:
        """Create a new support ticket."""
        ticket = Ticket(
            user_id=user_id,
            subject=data.subject,
            description=data.description
        )
        
        # Add initial message
        initial_message = TicketMessage(
            sender_id=user_id,
            sender_name=user_name,
            is_staff=False,
            content=data.description
        )
        ticket.messages.append(initial_message)
        
        ticket_dict = ticket.model_dump(by_alias=True)
        await self.db.tickets.insert_one(ticket_dict)
        
        return ticket
    
    async def get_user_tickets(self, user_id: str) -> List[Ticket]:
        """Get all tickets for a user."""
        cursor = self.db.tickets.find({"user_id": user_id}).sort("created_at", -1)
        tickets = []
        async for doc in cursor:
            tickets.append(Ticket(**serialize_doc(doc)))
        return tickets
    
    async def get_all_tickets(self, status_filter: Optional[str] = None) -> List[Ticket]:
        """Get all tickets (admin)."""
        query = {}
        if status_filter and status_filter != 'all':
            query["status"] = status_filter
        
        cursor = self.db.tickets.find(query).sort("updated_at", -1).limit(100)
        tickets = []
        async for doc in cursor:
            tickets.append(Ticket(**serialize_doc(doc)))
        return tickets
    
    async def add_message(
        self,
        ticket_id: str,
        sender_id: str,
        sender_name: str,
        is_staff: bool,
        data: MessageCreate
    ) -> Ticket:
        """Add a message to a ticket."""
        ticket_doc = await self.db.tickets.find_one({"_id": ticket_id})
        if not ticket_doc:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        message = TicketMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            is_staff=is_staff,
            content=data.content
        )
        
        await self.db.tickets.update_one(
            {"_id": ticket_id},
            {
                "$push": {"messages": message.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        ticket_doc = await self.db.tickets.find_one({"_id": ticket_id})
        return Ticket(**serialize_doc(ticket_doc))
    
    async def update_ticket_status(
        self,
        ticket_id: str,
        new_status: TicketStatus,
        assigned_to: Optional[str] = None
    ) -> Ticket:
        """Update ticket status (admin)."""
        update_data = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        if new_status == TicketStatus.RESOLVED:
            update_data["resolved_at"] = datetime.utcnow()
        
        if assigned_to:
            update_data["assigned_to"] = assigned_to
        
        await self.db.tickets.update_one(
            {"_id": ticket_id},
            {"$set": update_data}
        )
        
        ticket_doc = await self.db.tickets.find_one({"_id": ticket_id})
        return Ticket(**serialize_doc(ticket_doc))