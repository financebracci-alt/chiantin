"""Common utilities and helpers."""

from typing import Any, Dict
from datetime import datetime
from bson import ObjectId
import hashlib


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize MongoDB document for JSON response.
    
    Converts ObjectId to string and datetime to ISO format with 'Z' suffix for UTC.
    """
    if doc is None:
        return None
    
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            # Add 'Z' suffix for UTC timezone indicator (ISO 8601 compliant)
            iso_str = value.isoformat()
            if not iso_str.endswith('Z') and '+' not in iso_str and iso_str.count('-') < 3:
                iso_str += 'Z'
            result[key] = iso_str
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    
    # Convert _id to id
    if "_id" in result:
        result["id"] = result.pop("_id")
    
    return result


def hash_refresh_token(token: str) -> str:
    """Hash refresh token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_account_number() -> str:
    """Generate a random account number."""
    import secrets
    return f"ACC{secrets.randbelow(10**12):012d}"


def generate_sandbox_iban(country: str = "DE") -> str:
    """Generate a sandbox IBAN (not real, for testing only)."""
    import secrets
    # DE IBAN format: DE + 2 check digits + 18 digits
    digits = f"{secrets.randbelow(10**18):018d}"
    return f"{country}99{digits}"


def generate_bic() -> str:
    """Generate a sandbox BIC (not real)."""
    return "ATLASDE99XXX"