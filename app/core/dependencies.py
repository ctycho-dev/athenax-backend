import os
import certifi
import urllib
import jwt
from jwt import PyJWKClient
from jose import JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.infrastructure.repository.wishlist import WishlistRepository
from app.infrastructure.repository.audit import AuditRepository
from app.infrastructure.repository.research import ResearchRepository
from app.infrastructure.repository.user import UserRepository
from app.core.config import settings
from app.core.logger import get_logger

# Set the SSL certificate path explicitly
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()

security = HTTPBearer(auto_error=False)  # Don't auto-raise 401


logger = get_logger()


jwks_client = PyJWKClient(
    settings.PRIVY_JWSK_URL,
    timeout=10,
    max_cached_keys=5,
    cache_keys=True
)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependency that verifies Privy JWT and returns decoded token
    Raises 401 if token is invalid
    """
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(creds.credentials)
        
        decoded = jwt.decode(
            creds.credentials,
            signing_key.key,
            issuer="privy.io",
            audience=settings.PRIVY_APP_ID,
            algorithms=["ES256"]
        )
        return decoded['sub']
    except urllib.error.URLError as e:
        logger.error("Network error accessing JWKS URL: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Authentication service unavailable"
        ) from e
    except jwt.PyJWKClientError as e:
        logger.error("JWKS client error: %s", e)
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve signing keys"
        ) from e
    except JWTError as e:
        logger.error('Invalid authentication credentials')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except Exception as e:
        logger.error('Get Current User: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        ) from e


def get_user_repo() -> UserRepository:

    return UserRepository()


def get_wislist_repo() -> WishlistRepository:

    return WishlistRepository()


def get_audit_repo() -> AuditRepository:

    return AuditRepository()


def get_research_repo() -> ResearchRepository:

    return ResearchRepository()
