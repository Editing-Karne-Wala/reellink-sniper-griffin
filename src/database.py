from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from .config import DATABASE_URL

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    scan_count = Column(Integer, default=0)
    last_scanned = Column(DateTime, default=datetime.utcnow)
    is_pro = Column(Boolean, default=False)
    # Add other fields for monetization, e.g., affiliate commissions, payment status

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username='{self.username}', scan_count={self.scan_count})>"

# Add other models as needed, e.g., for affiliate programs, detected tools

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_or_create_user(telegram_id, username=None):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        session.commit()
    session.close()
    return user

# Add functions for updating scan counts, checking limits, etc.
