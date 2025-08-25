import os
import certifi
import urllib
import jwt
from jwt import PyJWKClient
from jose import JWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.domain.wishlist.repository import WishlistRepository
from app.domain.submit.audit.repository import AuditRepository
from app.domain.submit.research.repository import ResearchRepository
from app.domain.user.repository import UserRepository
from app.domain.profile.repository import ProfileRepository
from app.domain.user.schema import UserOut
from app.core.config import settings
from app.core.logger import get_logger
from app.domain.user.model import User
from app.domain.submit.audit.service import AuditService
from app.domain.submit.research.service import ResearchService
# from app.services.storj import StorjService
from app.domain.user.service import UserService
from app.domain.profile.service import ProfileService
from app.domain.article.repository import ArticleRepository
from app.domain.article.service import ArticleService
from app.utils.serialize import serialize

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


def get_user_repo() -> UserRepository:

    return UserRepository()


def get_profile_repo() -> ProfileRepository:

    return ProfileRepository()


def get_wislist_repo() -> WishlistRepository:

    return WishlistRepository()


def get_audit_repo() -> AuditRepository:

    return AuditRepository()


def get_research_repo() -> ResearchRepository:

    return ResearchRepository()

def get_article_repo() -> ArticleRepository:

    return ArticleRepository()


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repo)
) -> User:
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
            algorithms=["ES256"],
            leeway=10
        )
        user_id = decoded['sub']
        request.state.user = user_id

        user = await user_repo.get_by_privy_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user
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
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error('Get Current User: %s', e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        ) from e


def get_current_user_out(
    user: User = Depends(get_current_user),
) -> UserOut:

    user_dict = serialize(user.model_dump())
    return UserOut(**user_dict)


async def get_optional_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(security),
    user_repo: UserRepository = Depends(get_user_repo)
) -> User | None:
    if not creds:
        return None

    try:
        return await get_current_user(request, creds, user_repo)
    except HTTPException as e:
        if e.status_code in {401, 404, 502}:
            return None  # Treat as unauthenticated
        raise
    except Exception as e:
        logger.warning("Optional user failed: %s", e)
        return None


def get_user_service(
    repo: UserRepository = Depends(get_user_repo),
) -> UserService:
    return UserService(repo)


def get_audit_service(
    repo: AuditRepository = Depends(get_audit_repo),
    user: User = Depends(get_current_user),
):
    return AuditService(repo=repo, user=user)


def get_research_service(
    repo: ResearchRepository = Depends(get_research_repo),
    user: User = Depends(get_current_user),
):
    return ResearchService(repo=repo, user=user)


def get_article_service_with_auth(
    repo: ArticleRepository = Depends(get_article_repo),
    user: User = Depends(get_current_user)
) -> ArticleService:
    return ArticleService(repo=repo, user=user)


def get_article_service_optional(
    repo: ArticleRepository = Depends(get_article_repo),
    user: User | None = Depends(get_optional_user)
) -> ArticleService:
    return ArticleService(repo=repo, user=user)


def get_profile_service(
    repo: ProfileRepository = Depends(get_profile_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    user: UserOut = Depends(get_current_user_out)
) -> ProfileService:
    return ProfileService(repo=repo, user_repo=user_repo, user=user)
