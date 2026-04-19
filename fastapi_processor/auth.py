"""
JWT Authentication for FastAPI
Validates tokens signed by Django's SimpleJWT
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from config import settings

security = HTTPBearer()


class TokenPayload(BaseModel):
    user_id: int
    email: str = ""
    token_type: str = "access"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """
    Decode and validate the Bearer JWT token.
    The token was issued by Django's SimpleJWT.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        # Django SimpleJWT stores user_id in "user_id" claim
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception

        return TokenPayload(
            user_id=int(user_id),
            token_type=payload.get("token_type", "access"),
        )
    except JWTError:
        raise credentials_exception
