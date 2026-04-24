import os
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


@dataclass
class APIKeyInfo:
    key: str
    user_id: str
    role: UserRole


@dataclass
class AuthenticatedUser:
    user_id: str
    role: UserRole
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin


def parse_api_keys() -> Dict[str, APIKeyInfo]:
    keys_config = os.getenv("API_KEYS", "")
    if not keys_config:
        return {}
    
    api_keys = {}
    for key_entry in keys_config.split(","):
        key_entry = key_entry.strip()
        if not key_entry:
            continue
        
        parts = key_entry.split(":")
        if len(parts) >= 2:
            key = parts[0].strip()
            user_id = parts[1].strip()
            role = UserRole(parts[2].strip()) if len(parts) > 2 else UserRole.user
            
            if key and user_id:
                api_keys[key] = APIKeyInfo(
                    key=key,
                    user_id=user_id,
                    role=role
                )
    
    return api_keys


def get_api_key_info(api_key: str) -> Optional[APIKeyInfo]:
    api_keys = parse_api_keys()
    return api_keys.get(api_key)
