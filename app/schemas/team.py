from typing import Literal

from pydantic import BaseModel, EmailStr, Field

TEAM_ROLE = Literal["admin", "editor"]
TEAM_ROLES = ("admin", "editor")


class TeamMemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: TEAM_ROLE = "editor"


class TeamMemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    role: TEAM_ROLE | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
