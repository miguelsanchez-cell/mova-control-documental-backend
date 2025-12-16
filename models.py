from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    grupo = Column(String, index=True)
    cema = Column(String, index=True)
    comeq = Column(String, index=True)
    estado = Column(String, index=True)

    documentos = relationship("Documento", back_populates="equipo")


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), index=True)
    tipo_documento = Column(String, index=True)

    vigencia_desde = Column(Date, nullable=True)
    vigencia_hasta = Column(Date, nullable=True)

    equipo = relationship("Equipo", back_populates="documentos")


class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, default="lector")  # lector, editor, admin

