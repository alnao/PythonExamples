from datetime import datetime, timedelta
from typing import Optional

import bcrypt

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel


# In un progetto reale leggi queste variabili da env
SECRET_KEY = "change_me_with_a_random_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Finto database in memoria
fake_users_db: dict[str, dict] = {}


class User(BaseModel):
    username: str
    full_name: Optional[str] = None


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRegister(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None


class ServiceResponse(BaseModel):
    server_time: str
    message: str
    username: str


app = FastAPI(title="FastAPI JWT Auth Example")

# Limite bcrypt: 72 byte
BCRYPT_MAX_PASSWORD_LENGTH = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Tronca la password a 72 byte per la verifica (bcrypt limita a 72 byte)
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_LENGTH:
        password_bytes = password_bytes[:BCRYPT_MAX_PASSWORD_LENGTH]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    # bcrypt.checkpw richiede bytes, non string
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    # Valida che la password non superi i 72 byte di bcrypt
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password too long. Maximum length is {BCRYPT_MAX_PASSWORD_LENGTH} bytes. "
            f"Your password is {len(password_bytes)} bytes."
        )
    # Genera salt e hash la password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def get_user(username: str) -> Optional[UserInDB]:
    user = fake_users_db.get(username)
    if user:
        return UserInDB(**user)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")  # type: ignore[assignment]
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return User(username=user.username, full_name=user.full_name)


@app.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister) -> User:
    if user_data.username in fake_users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Valida lunghezza password
    try:
        hashed_password = get_password_hash(user_data.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    fake_users_db[user_data.username] = {
        "username": user_data.username,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
    }
    return User(username=user_data.username, full_name=user_data.full_name)


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@app.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.get("/service", response_model=ServiceResponse)
async def protected_service(current_user: User = Depends(get_current_user)) -> ServiceResponse:
    """Esempio di endpoint protetto che richiede un JWT valido."""
    return ServiceResponse(
        server_time=datetime.utcnow().isoformat(),
        message=f"Ciao {current_user.username}, il servizio autenticato funziona!",
        username=current_user.username,
    )


@app.get("/")
def root() -> dict:
    return {"message": "FastAPI JWT Auth example is running"}


