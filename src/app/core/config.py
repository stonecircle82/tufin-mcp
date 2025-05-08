from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from enum import Enum # Import Enum
from typing import Dict, Optional, List # Import Dict for typing, Optional for optional type, and List for lists

# Define Roles using Enum
class UserRole(str, Enum):
    ADMIN = "admin"
    TICKET_MANAGER = "ticket_manager"
    USER = "user"

class Settings(BaseSettings):
    # MCP Server Settings
    MCP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    # Define other server settings like environment (dev, prod) if needed

    # Tufin Connection Settings (Placeholders - Add actual URLs)
    TUFIN_SECURETRACK_URL: str = "https://your-securetrack-host"
    TUFIN_SECURECHANGE_URL: str = "https://your-securechange-host"
    TUFIN_USERNAME: str = "your_tufin_username"
    TUFIN_PASSWORD: str = "your_tufin_password" # Consider secure handling
    TUFIN_SSL_VERIFY: bool = True # Default to True for production safety
    TUFIN_API_TIMEOUT: float = 30.0 # Default timeout in seconds
    TUFIN_GRAPHQL_URL: Optional[str] = None # e.g., https://your-securetrack/sg/api/v1/graphql
    # Optionally add TUFIN_SSL_CERT_PATH: Optional[str] = None if using custom CA bundles

    # Security Settings (Placeholders - Generate strong secrets)
    # Example: openssl rand -hex 32
    API_KEY_SECRET: str = "change_this_strong_secret_for_api_keys"
    MCP_API_KEY: str = "your_master_api_key" # Keep the master key concept if needed, or rely solely on role map

    # --- RBAC Settings --- 
    # WARNING: Storing keys and roles directly in config/env is INSECURE for production.
    # Use a database or secure store in a real application.
    # Maps Permission Identifiers (strings) to lists of allowed UserRoles
    # Use meaningful identifiers related to the action being performed.
    ENDPOINT_PERMISSIONS: Dict[str, List[UserRole]] = {
        "health_check": [], # No role required - handled by exempting
        "access_secure_endpoint": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "list_devices": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "get_device": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "list_tickets": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "create_ticket": [UserRole.ADMIN, UserRole.TICKET_MANAGER],
        # Add placeholders for others
        "get_ticket": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "update_ticket": [UserRole.ADMIN, UserRole.TICKET_MANAGER],
        "get_topology_path": [UserRole.ADMIN, UserRole.TICKET_MANAGER],
        "get_topology_path_image": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "add_devices": [UserRole.ADMIN],
        "import_managed_devices": [UserRole.ADMIN],
        "query_rules_graphql": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "test_tufin_connection": [UserRole.ADMIN],
    }

    # Maps allowable Workflow Names to list of roles that can create tickets for them
    # Example: {"Firewall Rule Change": [UserRole.ADMIN, UserRole.TICKET_MANAGER], "Server Decom": [UserRole.ADMIN]}
    # Needs configuration based on actual Tufin workflow names
    ALLOWED_WORKFLOWS: Dict[str, List[UserRole]] = {
        "Example Firewall Workflow": [UserRole.ADMIN, UserRole.TICKET_MANAGER, UserRole.USER],
        "Example Decom Workflow": [UserRole.ADMIN, UserRole.TICKET_MANAGER],
    }

    # --- Development Settings --- 
    # Used by InMemorySecureStore to load initial keys/roles during startup
    # Set this env var with a JSON string: '[{"key":"key_value", "role":"admin"}, ...]'
    # THIS IS NOT FOR PRODUCTION SECRETS.
    DEV_API_KEYS: Optional[str] = None

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_file='.env', # Load from .env file
        env_file_encoding='utf-8',
        extra='ignore' # Ignore extra fields from env
    )

# Cache the settings instance for efficiency
@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
