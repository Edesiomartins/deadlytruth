from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str
    nickname: str | None = None  # Opcional no registro


class UserOut(BaseModel):
    id: int
    email: str
    nickname: str | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    nickname: str


class Token(BaseModel):
    access_token: str
    token_type: str
