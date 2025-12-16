from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cadena de conexión para SQLite local
DATABASE_URL = "sqlite:///./test.db"

# Crea el motor de la base de datos
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Crea una sesión para interactuar con la base de datos
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Clase base para modelos ORM
Base = declarative_base()
