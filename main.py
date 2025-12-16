from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from models import Documento, Equipo, User
from schemas import UserCreate, UserOut

# -------------------------------------------
# CONFIGURACIÓN BASE
# -------------------------------------------
app = FastAPI()

# CORS para poder llamar desde index.html (en producción limita a tu dominio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# -------------------------------------------
# DB DEPENDENCY
# -------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------
# AUTH / JWT
# -------------------------------------------
SECRET_KEY = "CAMBIA_ESTA_CLAVE_SECRETA_LARGA_Y_UNICA"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Usar pbkdf2_sha256 en vez de bcrypt para evitar problemas de versión
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def require_role(*roles):
    def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.rol not in roles:
            raise HTTPException(status_code=403, detail="No tiene permisos suficientes")
        return current_user
    return checker

# -------------------------------------------
# RUTAS DE AUTH
# -------------------------------------------
@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    access_token = create_access_token(
        data={"sub": user.username, "rol": user.rol},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "rol": user.rol,
    }


@app.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.post("/register", response_model=UserOut, dependencies=[Depends(require_role("admin"))])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Solo admin puede crear usuarios
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    db_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        rol="lector",  # todos empiezan como lector
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# -------------------------------------------
# RUTAS EXISTENTES DOCUMENTOS
# -------------------------------------------
@app.get("/")
def read_root():
    return {"message": "API funcionando"}


@app.get("/documentos")
def listar_documentos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),  # requiere login
):
    filas = (
        db.query(Documento, Equipo)
        .join(Equipo, Documento.equipo_id == Equipo.id)
        .all()
    )

    resultado = []
    for doc, eq in filas:
        resultado.append(
            {
                "id": doc.id,
                "tipo_documento": doc.tipo_documento,
                "grupo": eq.grupo,
                "cema": eq.cema,
                "comeq": eq.comeq,
                "estado": eq.estado,
                "vigencia_desde": doc.vigencia_desde.isoformat()
                if doc.vigencia_desde
                else None,
                "vigencia_hasta": doc.vigencia_hasta.isoformat()
                if doc.vigencia_hasta
                else None,
            }
        )
    return resultado

