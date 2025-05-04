import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from .config import settings, UserRole
# Import the secure store instance
from .secure_store import secure_store_instance, SecureStore 

logger = logging.getLogger(__name__)

# --- API Key Security --- 

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Define a type for the dependency result
class AuthenticatedUser:
    def __init__(self, api_key: str, role: UserRole):
        self.api_key = api_key # Store raw key for potential logging/context
        self.role = role

async def get_authenticated_user(
    api_key_header: str = Depends(API_KEY_HEADER),
    store: SecureStore = Depends(lambda: secure_store_instance) # Inject store instance
) -> AuthenticatedUser:
    """Dependency to verify API key header using secure store and return user info."""
    if not api_key_header:
        logger.warning("Attempted access without API Key.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key in X-API-Key header",
        )

    # Verify the key against stored hashes and get role
    user_role = await store.verify_key_and_get_role(api_key_header)

    if user_role is None:
        logger.warning(f"Invalid API Key provided (verification failed): {api_key_header[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    # Key is valid, return user info object
    logger.info(f"API Key validated for role '{user_role.value}': {api_key_header[:5]}...")
    return AuthenticatedUser(api_key=api_key_header, role=user_role)

# --- RBAC Dependency (Updated) --- 

def require_permission(permission_id: str):
    """Factory function to create a dependency that checks user role against configured permissions."""
    async def permission_checker(current_user: AuthenticatedUser = Depends(get_authenticated_user)) -> AuthenticatedUser:
        """Checks if the authenticated user's role allows the required permission."""
        
        allowed_roles = settings.ENDPOINT_PERMISSIONS.get(permission_id)
        
        if allowed_roles is None:
            # Permission ID not configured - deny access as a security measure
            logger.error(f"Permission check failed: Permission ID '{permission_id}' not found in configuration.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Or 403?
                detail="Permission configuration error."
            )
        
        # Allow if the permission is explicitly empty (e.g., public access if auth passed)
        # Note: This check might not be strictly necessary if get_authenticated_user always requires a valid key/role
        # if not allowed_roles:
        #     return current_user
            
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Permission denied for '{permission_id}': Key {current_user.api_key[:5]}... has role '{current_user.role.value}', "
                f"requires one of '{[r.value for r in allowed_roles]}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Insufficient permissions. Requires permission: '{permission_id}'"
            )
        
        logger.info(
            f"Permission check passed for '{permission_id}': Key {current_user.api_key[:5]}... (Role: {current_user.role.value})"
        )
        return current_user # Return authenticated user object
    return permission_checker