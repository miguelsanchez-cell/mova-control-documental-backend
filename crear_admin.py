from database import SessionLocal
from models import User
from main import get_password_hash, get_user_by_username

def crear_admin():
    db = SessionLocal()
    try:
        if get_user_by_username(db, "admin"):
            print("Ya existe un usuario admin")
            return
        admin = User(
            username="admin",
            password_hash=get_password_hash("admin"),
            rol="admin",
        )
        db.add(admin)
        db.commit()
        print("Usuario admin creado con contraseña 'admin'")
    finally:
        db.close()

if __name__ == "__main__":
    crear_admin()
