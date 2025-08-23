from sqlalchemy import Column, Integer, String, Boolean, PickleType, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    keywords = Column(PickleType, default=[])
    active = Column(Boolean, default=False)
    filtered_messages = relationship("FilteredMessage", back_populates="user", cascade="all, delete-orphan")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    type = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class FilteredMessage(Base):
    __tablename__ = "filtered_messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    sender_name = Column(String, nullable=True)       # اسم المستخدم الذي أرسل الرسالة
    group_link = Column(String, nullable=True)        # رابط المجموعة التي أرسلت فيها الرسالة
    message_link = Column(String, nullable=True)      # رابط الرسالة

    user = relationship("User", back_populates="filtered_messages")

engine = create_engine('sqlite:///telegram_bot.db')
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
