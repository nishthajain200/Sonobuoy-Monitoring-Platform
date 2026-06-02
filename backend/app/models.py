"""SQLAlchemy ORM models."""
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Text
from .database import Base


class Sonobuoy(Base):
    __tablename__ = "sonobuoys"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    deployment_time = Column(DateTime, nullable=False)
    number_of_channels = Column(Integer, default=4)
    sample_rate = Column(Integer, default=48000)
    recording_duration = Column(Float, default=600)
    status = Column(String, default="Active")
    wav_file = Column(String, nullable=True)


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sonobuoy_id = Column(String, nullable=False, index=True)
    channel = Column(Integer, nullable=False)
    fundamental_frequency = Column(Float, nullable=False)
    harmonics = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=True)


class BearingResult(Base):
    __tablename__ = "bearing_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sonobuoy_id = Column(String, nullable=False, index=True)
    bearing = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    frequency = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=True)


class LofarSignature(Base):
    __tablename__ = "lofar_signatures"

    id = Column(String, primary_key=True)
    platform_type = Column(String, nullable=False)
    fundamental_frequency = Column(Float, nullable=False)
    harmonics = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)


class LofarMatch(Base):
    __tablename__ = "lofar_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sonobuoy_id = Column(String, nullable=False, index=True)
    channel = Column(Integer, nullable=False)
    signature_id = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=True)


class MissionEvent(Base):
    __tablename__ = "mission_events"

    id = Column(String, primary_key=True)
    sonobuoy_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    channel = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    fundamental_frequency = Column(Float, nullable=True)
    harmonics = Column(JSON, nullable=True)
    bearing = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    lofar_match = Column(String, nullable=True)
    description = Column(Text, nullable=True)


class Correlation(Base):
    __tablename__ = "correlations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sonobuoy_id_a = Column(String, nullable=False)
    sonobuoy_id_b = Column(String, nullable=False)
    correlation_score = Column(Float, nullable=False)
    common_frequencies = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=True)
