"""Database models and management."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from config.settings import DB_PATH
from core.encryption import encryption
from utils.logger import app_logger

Base = declarative_base()


class Member(Base):
    """Member/Socio model - stores member data from backend."""
    __tablename__ = 'members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    backend_id = Column(Integer, unique=True, nullable=False, index=True)  # ID from backend
    name_encrypted = Column(String, nullable=False)  # Encrypted name
    email_encrypted = Column(String)  # Encrypted email (optional)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fingerprints = relationship("Fingerprint", back_populates="member", cascade="all, delete-orphan")
    
    @property
    def name(self) -> str:
        """Decrypt and return member name."""
        try:
            return encryption.decrypt(self.name_encrypted)
        except Exception:
            return "Unknown"
    
    @name.setter
    def name(self, value: str):
        """Encrypt and store member name."""
        self.name_encrypted = encryption.encrypt(value)
    
    @property
    def email(self) -> Optional[str]:
        """Decrypt and return member email."""
        if not self.email_encrypted:
            return None
        try:
            return encryption.decrypt(self.email_encrypted)
        except Exception:
            return None
    
    @email.setter
    def email(self, value: Optional[str]):
        """Encrypt and store member email."""
        if value:
            self.email_encrypted = encryption.encrypt(value)
        else:
            self.email_encrypted = None


class Fingerprint(Base):
    """Fingerprint model - stores biometric fingerprints."""
    __tablename__ = 'fingerprints'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('members.id'), nullable=False, index=True)
    template_encrypted = Column(LargeBinary, nullable=False)  # Encrypted fingerprint template
    finger_index = Column(Integer, nullable=False)  # 0-9 (which finger)
    quality = Column(Integer)  # Quality score from device
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="fingerprints")
    
    @property
    def template(self) -> bytes:
        """Decrypt and return fingerprint template."""
        try:
            return encryption.decrypt_bytes(self.template_encrypted)
        except Exception:
            return b""
    
    @template.setter
    def template(self, value: bytes):
        """Encrypt and store fingerprint template."""
        self.template_encrypted = encryption.encrypt_bytes(value)


class Setting(Base):
    """Settings model - stores app configuration."""
    __tablename__ = 'settings'
    
    key = Column(String, primary_key=True)
    value_encrypted = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def value(self) -> str:
        """Decrypt and return setting value."""
        try:
            return encryption.decrypt(self.value_encrypted)
        except Exception:
            return ""
    
    @value.setter
    def value(self, val: str):
        """Encrypt and store setting value."""
        self.value_encrypted = encryption.encrypt(val)


class Database:
    """Database manager."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database connection."""
        try:
            # Create SQLite database
            db_url = f"sqlite:///{DB_PATH}"
            self.engine = create_engine(db_url, echo=False)
            
            # Create tables
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            app_logger.info(f"Database initialized at: {DB_PATH}")
            
        except Exception as e:
            app_logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()
    
    def get_or_create_member(self, backend_id: int, name: str, email: Optional[str] = None) -> Member:
        """Get or create member.
        
        Args:
            backend_id: Member ID from backend
            name: Member name
            email: Member email (optional)
            
        Returns:
            Member instance
        """
        session = self.get_session()
        try:
            member = session.query(Member).filter_by(backend_id=backend_id).first()
            
            if not member:
                member = Member(backend_id=backend_id)
                member.name = name
                member.email = email
                session.add(member)
                session.commit()
                app_logger.info(f"Created new member: {backend_id}")
            else:
                # Update if changed
                if member.name != name or member.email != email:
                    member.name = name
                    member.email = email
                    session.commit()
                    app_logger.info(f"Updated member: {backend_id}")
            
            return member
        finally:
            session.close()
    
    def store_fingerprint(self, backend_id: int, template: bytes, finger_index: int, quality: int = 0) -> bool:
        """Store fingerprint for member.
        
        Args:
            backend_id: Member ID from backend
            template: Fingerprint template (binary)
            finger_index: Which finger (0-9)
            quality: Quality score
            
        Returns:
            True if successful
        """
        session = self.get_session()
        try:
            member = session.query(Member).filter_by(backend_id=backend_id).first()
            if not member:
                app_logger.error(f"Member not found: {backend_id}")
                return False
            
            # Check if fingerprint already exists
            fp = session.query(Fingerprint).filter_by(
                member_id=member.id,
                finger_index=finger_index
            ).first()
            
            if fp:
                # Update existing
                fp.template = template
                fp.quality = quality
                app_logger.info(f"Updated fingerprint for member {backend_id}, finger {finger_index}")
            else:
                # Create new
                fp = Fingerprint(
                    member_id=member.id,
                    finger_index=finger_index,
                    quality=quality
                )
                fp.template = template
                session.add(fp)
                app_logger.info(f"Stored new fingerprint for member {backend_id}, finger {finger_index}")
            
            session.commit()
            return True
            
        except Exception as e:
            app_logger.error(f"Failed to store fingerprint: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_member_fingerprints(self, backend_id: int) -> List[Fingerprint]:
        """Get all fingerprints for a member.
        
        Args:
            backend_id: Member ID from backend
            
        Returns:
            List of fingerprints
        """
        session = self.get_session()
        try:
            member = session.query(Member).filter_by(backend_id=backend_id).first()
            if not member:
                return []
            return member.fingerprints
        finally:
            session.close()
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get setting value.
        
        Args:
            key: Setting key
            
        Returns:
            Setting value or None
        """
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            return setting.value if setting else None
        finally:
            session.close()
    
    def set_setting(self, key: str, value: str):
        """Set setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        session = self.get_session()
        try:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key)
                setting.value = value
                session.add(setting)
            session.commit()
        finally:
            session.close()


# Singleton instance
database = Database()
