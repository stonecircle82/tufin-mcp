from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any
import logging
import json
from passlib.context import CryptContext

from .config import UserRole, settings

logger = logging.getLogger(__name__)

# Configure passlib
# Using bcrypt as it's suitable for API keys (though designed for passwords)
# Schemes can be expanded later if needed.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecureStore(ABC):
    """Abstract Base Class for secure API key storage and validation."""
    
    @abstractmethod
    async def load_initial_keys(self):
        """Load initial keys/roles (e.g., for development/bootstrapping)."""
        pass

    @abstractmethod
    async def verify_key_and_get_role(self, api_key: str) -> Optional[UserRole]:
        """Verify the provided API key against stored hashes and return its role."""
        pass

    @abstractmethod
    async def add_key(self, api_key: str, role: UserRole):
        """(For Management) Add a new hashed key and role."""
        pass

    @abstractmethod
    async def revoke_key(self, api_key_hash_or_prefix: str):
        """(For Management) Revoke a key."""
        pass

# --- In-Memory Implementation (for Development/Testing) ---

class InMemorySecureStore(SecureStore):
    """In-memory store using a dictionary. NOT FOR PRODUCTION SECRETS."""
    def __init__(self):
        # Stores: {hashed_key: role}
        self._storage: Dict[str, UserRole] = {}
        self._raw_keys_for_verification: Dict[str, str] = {} # {raw_key: hashed_key} - only used if verify() needs raw hash

    def _hash_key(self, api_key: str) -> str:
        return pwd_context.hash(api_key)

    def _verify_key(self, api_key: str, hashed_key: str) -> bool:
        return pwd_context.verify(api_key, hashed_key)

    async def load_initial_keys(self):
        # Load from DEV_API_KEYS environment variable (JSON string expected)
        # Example: '[{"key":"admin_key_abc", "role":"admin"}, {"key":"user_key_123", "role":"user"}]'
        dev_keys_json = settings.DEV_API_KEYS
        if not dev_keys_json:
            logger.warning("DEV_API_KEYS not set. No initial keys loaded for in-memory store.")
            return
            
        try:
            dev_keys: List[Dict[str, str]] = json.loads(dev_keys_json)
            count = 0
            for item in dev_keys:
                key = item.get('key')
                role_str = item.get('role')
                if key and role_str:
                    try:
                        role = UserRole(role_str)
                        hashed_key = self._hash_key(key)
                        self._storage[hashed_key] = role
                        # self._raw_keys_for_verification[key] = hashed_key # Only store if needed for specific verify logic
                        count += 1
                    except ValueError:
                        logger.error(f"Invalid role '{role_str}' found in DEV_API_KEYS for key prefix {key[:5]}...")
                    except Exception as e:
                        logger.error(f"Error hashing/storing dev key {key[:5]}...: {e}")
                else:
                    logger.warning(f"Skipping invalid entry in DEV_API_KEYS: {item}")
            logger.info(f"Loaded {count} initial API keys into in-memory store from DEV_API_KEYS.")
        except json.JSONDecodeError:
            logger.error("Failed to parse DEV_API_KEYS as JSON. Please provide a valid JSON list.")
        except Exception as e:
            logger.error(f"Error processing DEV_API_KEYS: {e}")

    async def verify_key_and_get_role(self, api_key: str) -> Optional[UserRole]:
        # Iterate through stored hashes and verify
        for hashed_key, role in self._storage.items():
            try:
                if self._verify_key(api_key, hashed_key):
                    # logger.debug(f"Verified API key prefix {api_key[:5]}... against stored hash. Role: {role.value}")
                    return role
            except Exception as e:
                # Log potential verification errors (e.g., mismatching hash format)
                logger.error(f"Error verifying key {api_key[:5]}... against stored hash: {e}", exc_info=True)
                # Continue checking other hashes just in case, but this indicates a problem
                
        logger.warning(f"Failed verification attempt for API key prefix {api_key[:5]}...")
        return None

    async def add_key(self, api_key: str, role: UserRole):
        # Placeholder: In a real app, this would be part of a secure management process
        hashed_key = self._hash_key(api_key)
        self._storage[hashed_key] = role
        logger.info(f"(DEV) Added/Updated key with hash {hashed_key[:10]}... for role {role.value}")

    async def revoke_key(self, api_key_hash_or_prefix: str):
        # Placeholder: Needs a way to identify the key to revoke securely
        # This simple implementation just removes if hash matches exactly.
        if api_key_hash_or_prefix in self._storage:
            del self._storage[api_key_hash_or_prefix]
            logger.info(f"(DEV) Revoked key with hash {api_key_hash_or_prefix[:10]}...")
        else:
            logger.warning(f"(DEV) Attempted to revoke non-existent key hash {api_key_hash_or_prefix[:10]}...")

# --- Singleton Instance --- 
# Choose the store implementation (In-Memory for now)
# Replace with DBStore() or VaultStore() for production
secure_store_instance: SecureStore = InMemorySecureStore() 