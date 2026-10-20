from datetime import datetime, timedelta, timezone
import jwt
from app.config import settings


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token.

    :param data: The data to encode in the token (usually user information).
    :param secret_key: The secret key used to sign the token.
    :param algorithm: The algorithm used for encoding (default is HS256).
    :return: A JWT access token as a string.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    payload = {"user_id": user_id, "exp": expire}

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    Decode a JWT access token.

    :param token: The JWT access token to decode.
    :param secret_key: The secret key used to sign the token.
    :param algorithms: A list of algorithms to use for decoding (default is HS256).
    :return: The decoded payload as a dictionary.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
