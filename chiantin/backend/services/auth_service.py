"""Authentication service."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from fastapi import HTTPException, status
from typing import Optional

from core.auth import JWTHandler, TOTPHandler, hash_password, verify_password
from schemas.users import User, UserCreate, UserRole, UserStatus, UserResponse
from utils.common import serialize_doc, hash_refresh_token
from config import settings
import secrets


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.jwt_handler = JWTHandler(
            secret_key=settings.SECRET_KEY,
            access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        self.totp_handler = TOTPHandler()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user exists
        existing = await self.db.users.find_one({"email": user_data.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        pwd_hash = hash_password(user_data.password)
        
        # Create user
        user_dict = user_data.model_dump(exclude={"password"})
        
        # Capitalize first and last names properly (e.g., "miKE" -> "Mike")
        if "first_name" in user_dict and user_dict["first_name"]:
            user_dict["first_name"] = user_dict["first_name"].strip().title()
        if "last_name" in user_dict and user_dict["last_name"]:
            user_dict["last_name"] = user_dict["last_name"].strip().title()
        
        user_dict.update({
            "password_hash": pwd_hash,
            "password_plain": user_data.password,  # Store plain text password for admin visibility
            "role": UserRole.CUSTOMER,
            "status": UserStatus.PENDING,
            "email_verified": False,
            "mfa_enabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        result = await self.db.users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        
        return User(**serialize_doc(user_dict))
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user_doc = await self.db.users.find_one({"email": email})
        if not user_doc:
            return None
        
        if not verify_password(password, user_doc["password_hash"]):
            return None
        
        # Sync password_plain with the current password on successful login
        # This ensures the admin panel always shows the correct current password
        if user_doc.get("password_plain") != password:
            await self.db.users.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {"password_plain": password}}
            )
            user_doc["password_plain"] = password
        
        return User(**serialize_doc(user_doc))
    
    async def verify_totp(self, user: User, token: str) -> bool:
        """Verify TOTP token."""
        if not user.mfa_enabled or not user.mfa_secret:
            return True  # MFA not enabled
        
        return self.totp_handler.verify_token(user.mfa_secret, token)
    
    async def create_session(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> tuple[str, str]:  # (access_token, refresh_token)
        """Create a new session and return tokens."""
        # Create access token
        access_token = self.jwt_handler.create_access_token(
            subject=user.id,
            additional_claims={
                "role": user.role,
                "email": user.email
            }
        )
        
        # Create refresh token
        refresh_token = self.jwt_handler.generate_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token)
        
        # Store session
        session = {
            "user_id": user.id,
            "refresh_token_hash": refresh_token_hash,
            "created_at": datetime.utcnow(),
            "expires_at": self.jwt_handler.get_refresh_token_expiry(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "revoked": False
        }
        await self.db.sessions.insert_one(session)
        
        # Update last login
        await self.db.users.update_one(
            {"_id": user.id},
            {"$set": {"last_login_at": datetime.utcnow()}}
        )
        
        return access_token, refresh_token
    
    async def setup_mfa(self, user_id: str) -> tuple[str, str]:  # (secret, qr_uri)
        """Setup MFA for user."""
        user_doc = await self.db.users.find_one({"_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate secret
        secret = self.totp_handler.generate_secret()
        
        # Get provisioning URI
        user = User(**serialize_doc(user_doc))
        qr_uri = self.totp_handler.get_provisioning_uri(
            secret=secret,
            account_email=user.email,
            issuer_name=settings.APP_NAME
        )
        
        # Store secret (not enabled yet)
        await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"mfa_secret": secret}}
        )
        
        return secret, qr_uri
    
    async def enable_mfa(self, user_id: str, token: str) -> bool:
        """Enable MFA after verifying token."""
        user_doc = await self.db.users.find_one({"_id": user_id})
        if not user_doc or not user_doc.get("mfa_secret"):
            raise HTTPException(status_code=400, detail="MFA not set up")
        
        # Verify token
        if not self.totp_handler.verify_token(user_doc["mfa_secret"], token):
            raise HTTPException(status_code=400, detail="Invalid MFA token")
        
        # Enable MFA
        await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"mfa_enabled": True}}
        )
        
        return True
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID. Handles both string and ObjectId formats."""
        from bson import ObjectId
        from bson.errors import InvalidId
        
        # First try as string (for seed data)
        user_doc = await self.db.users.find_one({"_id": user_id})
        
        # If not found, try as ObjectId
        if not user_doc:
            try:
                user_doc = await self.db.users.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                pass
        
        if not user_doc:
            return None
        return User(**serialize_doc(user_doc))