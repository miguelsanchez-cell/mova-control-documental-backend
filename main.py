from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os

DATABASE_URL = "sqlite:////tmp/mova.db"
SECRET_KEY = "tu_clave_secreta_super_segura_cambiar_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# Asegurar que /tmp existe
os.makedirs("/tmp", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    rol = Column(String, default="viewer")

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, index=True)
    grupo = Column(String)
    cema = Column(String)
    comeq = Column(String)
    tipo_documento = Column(String)
    vigencia_desde = Column(String)
    vigencia_hasta = Column(String)
    estado = Column(String)

Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def _truncate_password_to_72_bytes(password: str) -> str:
    """
    Trunca una contraseña a máximo 72 bytes (límite de bcrypt).
    Maneja caracteres multi-byte correctamente en UTF-8.
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncar a 72 bytes y decodificar, ignorando bytes incompletos
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return password

def hash_password(password: str) -> str:
    """Hashea una contraseña usando bcrypt con límite de 72 bytes."""
    password_limited = _truncate_password_to_72_bytes(password)
    return pwd_context.hash(password_limited)

def verify_password(plain: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    try:
        plain_limited = _truncate_password_to_72_bytes(plain)
        return pwd_context.verify(plain_limited, hashed)
    except Exception as e:
        return False

def create_access_token(data: dict):
    """Crea un JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Obtiene el usuario actual desde el JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="No autorizado")
    except JWTError:
        raise HTTPException(status_code=401, detail="No autorizado")
    
    session = SessionLocal()
    user = session.query(Usuario).filter(Usuario.username == username).first()
    session.close()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return {"username": user.username, "rol": user.rol}

class UsuarioCrear(BaseModel):
    username: str
    password: str
    rol: str = "viewer"

class DocumentoSchema(BaseModel):
    grupo: str = ""
    cema: str = ""
    comeq: str = ""
    tipo_documento: str = ""
    vigencia_desde: str = ""
    vigencia_hasta: str = ""
    estado: str = ""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def crear_admin():
    """Crea el usuario administrador si no existe."""
    session = SessionLocal()
    try:
        admin = session.query(Usuario).filter(Usuario.username == "admin").first()
        if not admin:
            new_admin = Usuario(
                username="admin",
                password_hash=hash_password("admin"),
                rol="admin"
            )
            session.add(new_admin)
            session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

# Crear admin al iniciar
crear_admin()

@app.get("/")
async def root():
    """Endpoint de salud."""
    return {"status": "ok"}

@app.post("/reset-db")
async def reset_database():
    """
    PELIGROSO: Elimina completamente la base de datos y la recrea.
    Úsalo solo en desarrollo o cuando necesites limpiar todo.
    Recrea el usuario admin con credenciales admin/admin.
    """
    try:
        # Eliminar el archivo de BD si existe
        db_path = "/tmp/mova.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        
        # Eliminar todas las tablas
        Base.metadata.drop_all(bind=engine)
        
        # Recrear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        # Crear admin nuevamente
        crear_admin()
        
        return {
            "mensaje": "✅ Base de datos eliminada y reiniciada",
            "admin_user": "admin",
            "admin_password": "admin"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al resetear BD: {str(e)}")

@app.post("/setup-admin")
async def setup_admin():
    """Endpoint para crear/verificar el usuario administrador."""
    crear_admin()
    return {"mensaje": "✅ Admin setup completado"}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint de login que retorna JWT token."""
    session = SessionLocal()
    try:
        user = session.query(Usuario).filter(Usuario.username == form_data.username).first()
        
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        token = create_access_token({"sub": user.username})
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.username,
            "rol": user.rol
        }
    finally:
        session.close()

@app.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Obtiene información del usuario actual."""
    return current_user

@app.post("/register")
async def register(usuario: UsuarioCrear, current_user: dict = Depends(get_current_user)):
    """Crea un nuevo usuario (solo admins)."""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo admins pueden crear usuarios")
    
    session = SessionLocal()
    try:
        existing = session.query(Usuario).filter(Usuario.username == usuario.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Usuario ya existe")
        
        new_user = Usuario(
            username=usuario.username,
            password_hash=hash_password(usuario.password),
            rol=usuario.rol
        )
        session.add(new_user)
        session.commit()
        
        return {
            "mensaje": "Usuario creado",
            "username": usuario.username,
            "rol": usuario.rol
        }
    finally:
        session.close()

@app.get("/documentos")
async def get_documentos(current_user: dict = Depends(get_current_user)):
    """Obtiene todos los documentos (requiere autenticación)."""
    session = SessionLocal()
    try:
        docs = session.query(Documento).all()
        return [
            {
                "id": d.id,
                "grupo": d.grupo,
                "cema": d.cema,
                "comeq": d.comeq,
                "tipo_documento": d.tipo_documento,
                "vigencia_desde": d.vigencia_desde,
                "vigencia_hasta": d.vigencia_hasta,
                "estado": d.estado
            }
            for d in docs
        ]
    finally:
        session.close()

@app.put("/documentos/{doc_id}")
async def actualizar_documento(
    doc_id: int,
    documento: DocumentoSchema,
    current_user: dict = Depends(get_current_user)
):
    """Actualiza un documento (requiere rol admin o editor)."""
    if current_user['rol'] not in ['admin', 'editor']:
        raise HTTPException(status_code=403, detail="No tiene permiso para editar")
    
    session = SessionLocal()
    try:
        doc = session.query(Documento).filter(Documento.id == doc_id).first()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Actualizar solo campos que tengan valores
        if documento.tipo_documento:
            doc.tipo_documento = documento.tipo_documento
        if documento.vigencia_desde:
            doc.vigencia_desde = documento.vigencia_desde
        if documento.vigencia_hasta:
            doc.vigencia_hasta = documento.vigencia_hasta
        if documento.estado:
            doc.estado = documento.estado
        if documento.grupo:
            doc.grupo = documento.grupo
        if documento.cema:
            doc.cema = documento.cema
        if documento.comeq:
            doc.comeq = documento.comeq
        
        session.commit()
        
        return {"mensaje": "Documento actualizado correctamente", "id": doc_id}
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


