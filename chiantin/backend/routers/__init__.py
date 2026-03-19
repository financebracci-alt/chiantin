"""
Routers package for the banking platform API.

Each router handles a specific domain of the application:
- auth: Authentication, signup, login, password reset
- admin_users: Admin user management
- admin_audit: Audit logging
- health: Health checks and debug endpoints
"""

from .dependencies import (
    get_current_user,
    require_admin,
    require_super_admin,
    create_audit_log,
    format_timestamp_utc
)

__all__ = [
    "get_current_user",
    "require_admin", 
    "require_super_admin",
    "create_audit_log",
    "format_timestamp_utc"
]
