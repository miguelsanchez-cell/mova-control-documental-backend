from pydantic import BaseModel
from typing import Optional
from datetime import date

# ---------------- EQUIPOS ----------------
class EquipoBase(BaseModel):
    grupo: Optional[str]
    cema: Optional[str]
    comeq: Optional[str]
    placa: Optional[str]
    estado: Optional[str]
    ubicacion: Optional[str]
    secretaria: Optional[str]
    notas: Optional[str]

class EquipoCreate(EquipoBase):
    pass

class Equipo(EquipoBase):
    id: int
    class Config:
        from_attributes = True

# ---------------- DOCUMENTOS --------------
class DocumentoBase(BaseModel):
    equipo_id: int
    tipo_documento: str
    fecha_emision: Optional[date]
    fecha_vencimiento: Optional[date]
    entidad_emisora: Optional[str]
    observaciones: Optional[str]

class DocumentoCreate(DocumentoBase):
    pass

class Documento(DocumentoBase):
    id: int
    class Config:
        from_attributes = True

# ---------------- USUARIOS ----------------
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    rol: str
    class Config:
        from_attributes = True

