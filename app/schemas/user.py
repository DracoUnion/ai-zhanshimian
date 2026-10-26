"""用户相关 Schema。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    nickname: str | None = None
    avatar_url: str | None = None
    unlocked: bool
    credits: int
    trial_used: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def trial_available(self) -> bool:
        return not self.trial_used


class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=512)