from sqlalchemy import Column, String, Text, Boolean, Date, Integer, ForeignKey, JSON, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    duration = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    availability = Column(Integer, nullable=False)
    booking_deadline = Column(Date, nullable=True)
    discounts = Column(Text, nullable=True)
    accommodation = Column(String(255), nullable=True)
    meals = Column(String(255), nullable=True)
    transportation = Column(String(255), nullable=True)
    tours = Column(Text, nullable=True)
    insurance = Column(Boolean, default=False)
    guides = Column(Text, nullable=True)
    additional_services = Column(Text, nullable=True)
    excluded_items = Column(Text, nullable=True)
    photos = Column(JSON, nullable=True)
    videos = Column(JSON, nullable=True)
    departure_location = Column(String(255), nullable=True)
    return_location = Column(String(255), nullable=True)
    meeting_points = Column(Text, nullable=True)
    itinerary = Column(Text, nullable=True)
    status = Column(String(50), default="activo")
    customizations = Column(Text, nullable=True)
    group_size = Column(String(50), nullable=True)
    travel_restrictions = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
