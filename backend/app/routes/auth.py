"""
AutoOps AI — Auth Routes.

Handles user signup, login, OTP multi-factor authentication, and profile retrieval.
Uses bcrypt for password hashing and JWT for session tokens.
"""

import random
import string
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..core.database import fetch_one, execute, fetch_val
from ..core.security import hash_password, verify_password, create_token, get_current_user
from ..schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserProfile
from ..core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

class OTPVerifyRequest(BaseModel):
    email: str
    otp: str

class ResendOTPRequest(BaseModel):
    email: str


def send_otp_email(to_email: str, otp: str):
    """Synchronous background task to send the OTP email using existing SMTP settings."""
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER
    password = settings.SMTP_PASS

    if not all([host, port, user, password]):
        print("MFA Warning: Missing SMTP configuration in .env -> Skipping actual email send.")
        print(f"MFA OTP for {to_email} is: {otp}") # Print to console for easy testing during hackathon
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = to_email
        msg["Subject"] = "Your Login OTP - AutoOps AI"

        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #ff385c;">AutoOps AI Security</h2>
                <p>Hello,</p>
                <p>Your one-time password (OTP) for login is:</p>
                <h1 style="background: #f4f4f4; padding: 10px; border-radius: 5px; display: inline-block; letter-spacing: 2px;">{otp}</h1>
                <p>This code will expire in 5 minutes. Do not share it with anyone.</p>
                <p>If you did not request this login, please ignore this email.</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
            
        print(f"OTP successfully sent to {to_email}")
    except Exception as e:
        print(f"Failed to send OTP email: {e}")


@router.post("/signup")
async def signup(req: SignupRequest):
    """Register a new user. Does not issue token; redirects to login flow."""
    existing = await fetch_one("SELECT id FROM users WHERE email = $1", req.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    pw_hash = hash_password(req.password)
    user_id = await fetch_val(
        """
        INSERT INTO users (full_name, email, password_hash, role, otp_verified)
        VALUES ($1, $2, $3, $4, FALSE)
        RETURNING id
        """,
        req.full_name, req.email, pw_hash, req.role,
    )

    return {"status": "success", "message": "Account created successfully. Please log in."}


@router.post("/login")
async def login(req: LoginRequest, background_tasks: BackgroundTasks):
    """Authenticate user and trigger the MFA OTP flow."""
    user = await fetch_one(
        "SELECT id, full_name, email, password_hash, role, is_active FROM users WHERE email = $1",
        req.email,
    )

    if not user or not user["is_active"] or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Proceed to MFA Flow
    otp_code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.now() + timedelta(minutes=5)

    # Invalidate any old OTPs for this user
    await execute("UPDATE otp_codes SET used = TRUE WHERE user_id = $1", user["id"])
    
    # Store the new OTP (idempotent design)
    await execute(
        "INSERT INTO otp_codes (user_id, email, otp, expires_at) VALUES ($1, $2, $3, $4)",
        user["id"], user["email"], otp_code, expires_at
    )
    
    # Temporarily mark user as unverified in the session DB context
    await execute("UPDATE users SET otp_verified = FALSE WHERE id = $1", user["id"])

    # Dispatch email asynchronously
    background_tasks.add_task(send_otp_email, user["email"], otp_code)

    return {
        "status": "otp_required",
        "email": user["email"],
        "message": "Valid credentials. Please verify the OTP sent to your email."
    }


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(req: OTPVerifyRequest):
    """Verify the 6-digit OTP and returning the authenticated JWT access token."""
    user = await fetch_one("SELECT id, role, full_name FROM users WHERE email = $1", req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    otp_record = await fetch_one(
        """
        SELECT id, expires_at, used 
        FROM otp_codes 
        WHERE email = $1 AND otp = $2
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        req.email, req.otp
    )

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")
    
    if otp_record["used"]:
        raise HTTPException(status_code=400, detail="OTP has already been used.")

    if otp_record["expires_at"] < datetime.now():
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # Validation passed - Mark OTP used and user verified
    await execute("UPDATE otp_codes SET used = TRUE WHERE id = $1", otp_record["id"])
    await execute("UPDATE users SET otp_verified = TRUE WHERE id = $1", user["id"])

    # Issue secure verified JWT token
    token = create_token(user["id"], user["role"], req.email, otp_verified=True)
    await execute("INSERT INTO sessions (user_id, token) VALUES ($1, $2)", user["id"], token)

    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        role=user["role"],
        full_name=user["full_name"]
    )


@router.post("/resend-otp")
async def resend_otp(req: ResendOTPRequest, background_tasks: BackgroundTasks):
    """Resend a new OTP to the email without needing the password again."""
    user = await fetch_one("SELECT id, email FROM users WHERE email = $1", req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    otp_code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.now() + timedelta(minutes=5)

    # Invalidate previous
    await execute("UPDATE otp_codes SET used = TRUE WHERE email = $1", user["email"])
    
    # Store new
    await execute(
        "INSERT INTO otp_codes (user_id, email, otp, expires_at) VALUES ($1, $2, $3, $4)",
        user["id"], user["email"], otp_code, expires_at
    )
    
    background_tasks.add_task(send_otp_email, user["email"], otp_code)

    return {"status": "otp_resent", "message": "A new OTP has been sent to your email."}


@router.get("/me", response_model=UserProfile)
async def get_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's profile. Blocked automatically if JWT is not otp_verified."""
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
