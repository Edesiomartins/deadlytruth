import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Garante que o .env local seja carregado ANTES de ler SECRET_KEY
# (este módulo é importado antes do load_dotenv() do main.py)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=False)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    _environment = os.getenv("ENVIRONMENT", "development").lower()
    if _environment == "production":
        # Nunca subir em produção sem chave: tokens forjáveis
        raise RuntimeError(
            "SECRET_KEY não configurada. Defina a variável de ambiente SECRET_KEY "
            "(ex: openssl rand -hex 32) antes de iniciar em produção."
        )
    # Em desenvolvimento, gera chave efêmera (tokens invalidam a cada restart)
    SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "⚠️ SECRET_KEY não definida — usando chave efêmera de desenvolvimento. "
        "Tokens serão invalidados a cada restart."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
