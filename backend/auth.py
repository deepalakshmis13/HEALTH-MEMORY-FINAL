"""Authentication dependencies and role guards."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from database import Session

from database import get_db
from models import Caregiver, Doctor, Patient, Reviewer, User
from utils.security import decode_access_token


class Principal:
    """The authenticated user plus their resolved role profile."""

    def __init__(self, user: User, profile=None):
        self.user = user
        self.profile = profile

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def name(self) -> str:
        return self.user.full_name

    @property
    def profile_id(self) -> Optional[int]:
        return getattr(self.profile, "id", None)

    @property
    def patient_id(self) -> Optional[int]:
        return self.profile.id if self.user.role == "patient" and self.profile else None


def _resolve_profile(db: Session, user: User):
    if user.role == "patient":
        return db.query(Patient).filter(Patient.user_id == user.id).first()
    if user.role == "doctor":
        return db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if user.role == "caregiver":
        return db.query(Caregiver).filter(Caregiver.user_id == user.id).first()
    if user.role == "reviewer":
        return db.query(Reviewer).filter(Reviewer.user_id == user.id).first()
    return None


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue.",
        )
    payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        )
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return Principal(user, _resolve_profile(db, user))


def require_roles(*roles: str):
    def dependency(principal: Principal = Depends(get_current_user)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this information.",
            )
        return principal

    return dependency
