from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.domain.user.schema import TokenData
from app.core.config import settings
from argon2 import PasswordHasher, exceptions as argon_exceptions

argon_hasher = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # Memory usage in kibibytes (64 MB)
    parallelism=4,      # Number of parallel threads
    hash_len=32,        # Length of the hash
    salt_len=16         # Length of the salt
)


SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict):
    """
    Create a JWT access token.

    Args:
        data (dict): The data to encode in the token.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()

    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str):
    """Decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc


def verify_access_token(token: str, credentials_exception):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get('user_id')

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(id=user_id)
    except JWTError as exc:
        raise credentials_exception from exc

    return token_data


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    Args:
        password (str): Plaintext password to hash.

    Returns:
        str: Argon2 hash.
    
    Raises:
        ValueError: If password is too short.
    """
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    return argon_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2 hash.

    Args:
        plain_password (str): Password to verify.
        hashed_password (str): Stored Argon2 hash.

    Returns:
        bool: True if password matches, False otherwise.
    """
    try:
        return argon_hasher.verify(hashed_password, plain_password)
    except (argon_exceptions.VerifyMismatchError, argon_exceptions.InvalidHashError):
        return False


def requires_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash should be rehashed (e.g., due to parameter change).

    Args:
        hashed_password (str): Stored Argon2 hash.

    Returns:
        bool: True if rehashing is recommended, False otherwise.
    """
    return argon_hasher.check_needs_rehash(hashed_password)


def create_temporary_access_token(file_id: int, expire_hours: int = 168) -> str:
    """
    Create a temporary JWT token with configurable expiration.
    
    Args:
        data (dict): The data to encode in the token
        expire_hours (int): Token expiration time in hours (default: 1)
    
    Returns:
        str: The encoded JWT token
    """
    payload = {
        "file_id": file_id,
        "purpose": "file_access",
        "exp": datetime.now() + timedelta(hours=expire_hours),
        "iat": datetime.now()
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def validate_file_access_token(token: str) -> int | None:
    """
    Validate file access token and extract file_id.
    
    Args:
        token: JWT token to validate
        
    Returns:
        file_id if token is valid and for file access, None otherwise
        
    Raises:
        ValueError: If token is expired, invalid, or wrong purpose
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("purpose") != "file_access":
            raise ValueError("Token is not for file access")

        file_id = payload.get("file_id")
        if file_id is None:
            raise ValueError("Token missing file_id")

        return file_id
    except JWTError as e:
        raise ValueError(f"Token validation failed: {str(e)}") from e
