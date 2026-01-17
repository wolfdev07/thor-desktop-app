from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import DB_PATH

Base = declarative_base()

class FingerPrint(Base):
    __tablename__ = 'fingerprints'

    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(String, unique=True, nullable=False)
    template = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class FingerPrintRepository:
    def __init__(self):
        self.db = SessionLocal()

    def save_fingerprint(self, uid: str, template: bytes):
        """Guarda o actualiza una huella en la DB."""
        try:
            new_fp = FingerPrint(uid=uid, template=template, created_at=datetime.now())
            self.db.add(new_fp)
            self.db.commit()
            self.db.refresh(new_fp)
            print( f"Fingerprint saved with ID: {new_fp.id}" )
            return new_fp
        except Exception as e:
            self.db.rollback()
            print( f"Error saving fingerprint: {e}" )
            raise e

    def get_all(self):
        """Obtiene todas las huellas para cargar en el lector al iniciar."""
        return self.db.query(FingerPrint).all()

    def get_by_id(self, internal_id: int):
        """Busca un usuario basado en el ID que retorna el lector (DBIdentify)."""
        return self.db.query(FingerPrint).filter(FingerPrint.id == internal_id).first()
    
    def close(self):
        self.db.close()


# Configuración de SQLite
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)