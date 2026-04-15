"""
AutoOps AI — Auth Routes.

Handles user signup, login, and profile retrieval.
Uses bcrypt for password hashing and JWT for session tokens.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any

from ..core.database import fetch_one, execute, fetch_val
from ..core.security import hash_password, verify_password, create_token, get_current_user
from ..schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse)
async def signup(req: SignupRequest):
    """Register a new user and return a JWT token."""

    # Check if email already exists
    existing = await fetch_one("SELECT id FROM users WHERE email = $1", req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password and insert user
    pw_hash = hash_password(req.password)
    user_id = await fetch_val(
        """
        INSERT INTO users (full_name, email, password_hash, role)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        req.full_name, req.email, pw_hash, req.role,
    )

    # Create JWT
    token = create_token(user_id, req.role, req.email)

    # Store session
    await execute(
        "INSERT INTO sessions (user_id, token) VALUES ($1, $2)",
        user_id, token,
    )

    return TokenResponse(
        access_token=token,
        user_id=user_id,
        role=req.role,
        full_name=req.full_name,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate user and return a JWT token."""

    user = await fetch_one(
        "SELECT id, full_name, email, password_hash, role, is_active FROM users WHERE email = $1",
        req.email,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create JWT
    token = create_token(user["id"], user["role"], user["email"])

    # Store session
    await execute(
        "INSERT INTO sessions (user_id, token) VALUES ($1, $2)",
        user["id"], token,
    )

    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        role=user["role"],
        full_name=user["full_name"],
    )


@router.get("/me", response_model=UserProfile)
async def get_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's profile."""
    row = await fetch_one(
        "SELECT id, full_name, email, role, is_active, created_at FROM users WHERE id = $1",
        user["user_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfile(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        role=row["role"],
        is_active=row["is_active"],
        created_at=str(row["created_at"]) if row["created_at"] else None,
    )
