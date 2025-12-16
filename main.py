from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import bcrypt
import os
import jwt
import json
from typing import Optional

# ===== CONFIGURACIÓN DE LA BASE DE DATOS =====
DATABASE_URL = "sqlite:///./mova.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== MODELOS DE BASE DE DATOS =====
class Usuario(Base):
    __tablename__ = "usuarios"
    username = Column(String(100), primary_key=True)
    password_hash = Column(String(255))
    rol = Column(String(20), default="user")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(200), nullable=False)
    contenido = Column(Text, nullable=False)
    autor = Column(String(100), nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ===== CREAR TABLAS =====
Base.metadata.create_all(bind=engine)

# ===== PYDANTIC MODELS =====
class UsuarioCrear(BaseModel):
    username: str
    password: str

class DocumentoSchema(BaseModel):
    id: Optional[int] = None
    titulo: str
    contenido: str
    autor: str
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True

# ===== FUNCIONES DE UTILIDAD =====
def hash_password(password: str) -> str:
    """Hashea la contraseña truncando a 72 bytes (límite de bcrypt)"""
    password_bytes = password.encode('utf-8')
    password_truncated = password_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_truncated, salt).decode('utf-8')

def verify_password(password: str, hash_stored: str) -> bool:
    """Verifica la contraseña contra el hash almacenado"""
    password_bytes = password.encode('utf-8')
    password_truncated = password_bytes[:72]
    return bcrypt.checkpw(password_truncated, hash_stored.encode('utf-8'))

def get_db():
    """Dependencia para obtener la sesión de BD"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== JWT =====
SECRET_KEY = "tu_secreto_super_seguro_aqui_12345"

def create_access_token(username: str, rol: str) -> str:
    """Crea un JWT token"""
    payload = {
        "username": username,
        "rol": rol,
        "token_type": "bearer"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def verify_token(token: str) -> dict:
    """Verifica y decodifica el JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        return None

# ===== FASTAPI APP =====
app = FastAPI(title="Mova Control Documental API")

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ENDPOINTS =====

@app.get("/")
def root():
    """Endpoint raíz"""
    return {"message": "Bienvenido a Mova Control Documental API"}

@app.post("/reset-db")
def reset_database(db: Session = Depends(get_db)):
    """
    PELIGROSO: Elimina completamente la base de datos y la recrea. 
    Úsalo solo en desarrollo o cuando necesites limpiar todo. 
    Recrea el usuario admin con credenciales admin/admin.
    """
    try:
        # Eliminar todas las tablas
        Base.metadata.drop_all(bind=engine)
        
        # Recrear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        # Crear usuario admin
        admin_user = Usuario(
            username="admin",
            password_hash=hash_password("admin"),
            rol="admin"
        )
        db.add(admin_user)
        db.commit()
        
        return {
            "mensaje": "Base de datos eliminada y reiniciada correctamente",
            "admin_user": "admin",
            "admin_password": "admin",
            "login_url": "/docs#/default/login_login_post"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/reset-users")
def reset_users_only(db: Session = Depends(get_db)):
    """
    Resetea SOLO la tabla de usuarios (preserva documentos).
    Elimina todos los usuarios existentes y recrea el usuario admin con credenciales admin/admin.
    Los documentos se mantienen intactos.
    """
    try:
        # Eliminar todos los usuarios
        db.query(Usuario).delete()
        db.commit()
        
        # Crear usuario admin nuevamente
        admin_user = Usuario(
            username="admin",
            password_hash=hash_password("admin"),
            rol="admin"
        )
        db.add(admin_user)
        db.commit()
        
        # Contar documentos preservados
        doc_count = db.query(Documento).count()
        
        return {
            "mensaje": "Tabla de usuarios reseteada correctamente",
            "admin_user": "admin",
            "admin_password": "admin",
            "documentos_preservados": doc_count,
            "login_url": "/docs#/default/login_login_post"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/setup-admin")
def setup_admin(usuario: UsuarioCrear, db: Session = Depends(get_db)):
    """Crea el usuario admin inicial"""
    try:
        existing = db.query(Usuario).filter_by(username=usuario.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Usuario ya existe")
        
        new_user = Usuario(
            username=usuario.username,
            password_hash=hash_password(usuario.password),
            rol="admin"
        )
        db.add(new_user)
        db.commit()
        return {"mensaje": f"Usuario {usuario.username} creado correctamente con rol admin"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    """
    Endpoint de login que retorna JWT token.
    """
    usuario = db.query(Usuario).filter_by(username=username).first()
    
    if not usuario or not verify_password(password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    token = create_access_token(usuario.username, usuario.rol)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": usuario.username,
        "rol": usuario.rol
    }

@app.get("/me")
def get_me(token: str = None, db: Session = Depends(get_db)):
    """Obtiene información del usuario actual basado en el token JWT"""
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    usuario = db.query(Usuario).filter_by(username=payload["username"]).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return {
        "username": usuario.username,
        "rol": usuario.rol,
        "fecha_creacion": usuario.fecha_creacion
    }

@app.post("/register")
def register(usuario: UsuarioCrear, db: Session = Depends(get_db)):
    """Registra un nuevo usuario"""
    existing = db.query(Usuario).filter_by(username=usuario.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")
    
    new_user = Usuario(
        username=usuario.username,
        password_hash=hash_password(usuario.password),
        rol="user"
    )
    db.add(new_user)
    db.commit()
    
    return {"mensaje": f"Usuario {usuario.username} registrado correctamente"}

@app.get("/documentos")
def get_documentos(db: Session = Depends(get_db)):
    """Obtiene todos los documentos"""
    documentos = db.query(Documento).all()
    return documentos

@app.post("/documentos")
def create_documento(documento: DocumentoSchema, db: Session = Depends(get_db)):
    """Crea un nuevo documento"""
    nuevo_doc = Documento(
        titulo=documento.titulo,
        contenido=documento.contenido,
        autor=documento.autor
    )
    db.add(nuevo_doc)
    db.commit()
    db.refresh(nuevo_doc)
    return nuevo_doc

@app.put("/documentos/{doc_id}")
def actualizar_documento(doc_id: int, documento: DocumentoSchema, db: Session = Depends(get_db)):
    """Actualiza un documento existente"""
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    doc.titulo = documento.titulo
    doc.contenido = documento.contenido
    doc.autor = documento.autor
    doc.fecha_actualizacion = datetime.utcnow()
    
    db.commit()
    db.refresh(doc)
    return doc

@app.delete("/documentos/{doc_id}")
def delete_documento(doc_id: int, db: Session = Depends(get_db)):
    """Elimina un documento"""
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    db.delete(doc)
    db.commit()
    return {"mensaje": "Documento eliminado correctamente"}

# ===== EJECUCIÓN =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


