from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from schemas import UserCreate, UserOut, UserUpdate, Token
from auth_utils import create_access_token, get_password_hash, verify_password, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=UserOut, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email já registrado.")
        
        # Verifica se nickname já existe (se fornecido)
        if user.nickname:
            try:
                existing_nickname = db.query(User).filter(User.nickname == user.nickname).first()
                if existing_nickname:
                    raise HTTPException(status_code=400, detail="Nickname já está em uso.")
            except Exception as e:
                # Se a coluna nickname não existir, ignora a verificação
                error_str = str(e).lower()
                if "nickname" in error_str or "column" in error_str or "does not exist" in error_str:
                    print("⚠️ Coluna nickname não existe ainda, pulando verificação")
                else:
                    raise

        hashed_password = get_password_hash(user.password)
        
        # Tenta criar com nickname, se falhar cria sem
        try:
            db_user = User(
                email=user.email, 
                hashed_password=hashed_password,
                nickname=user.nickname
            )
        except Exception as e:
            # Se falhar por causa da coluna nickname, cria sem ela
            print(f"⚠️ Erro ao criar com nickname, tentando sem: {e}")
            db_user = User(
                email=user.email, 
                hashed_password=hashed_password
            )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Garante que nickname seja None se não existir no banco
        if not hasattr(db_user, 'nickname'):
            db_user.nickname = None
            
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro no registro: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao criar usuário: {str(e)}")


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
        )

    access_token = create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
        )
    return user


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    # Garante que nickname seja None se não existir no banco
    if not hasattr(current_user, 'nickname'):
        current_user.nickname = None
    return current_user


@router.patch("/me/nickname", response_model=UserOut)
def update_nickname(nickname_update: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Atualiza o nickname do usuário"""
    # Verifica se nickname já existe (exceto o próprio usuário)
    existing_nickname = db.query(User).filter(
        User.nickname == nickname_update.nickname,
        User.id != current_user.id
    ).first()
    if existing_nickname:
        raise HTTPException(status_code=400, detail="Nickname já está em uso.")
    
    current_user.nickname = nickname_update.nickname
    db.commit()
    db.refresh(current_user)
    return current_user
