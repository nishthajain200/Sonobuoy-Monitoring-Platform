"""LOFAR signature matching engine."""
from sqlalchemy.orm import Session
from .models import LofarSignature, LofarMatch, Detection
from datetime import datetime


def seed_lofar_database(db: Session):
    """Seed the LOFAR signature database with realistic platform entries."""
    signatures = [
        LofarSignature(id="SIG001", platform_type="Kilo-class Submarine (877EKM)",
                       fundamental_frequency=50, harmonics=[100, 150, 200],
                       description="Diesel-electric submarine, diesel-generator tonal 50 Hz, blade-rate 8 Hz, low-speed transit"),
        LofarSignature(id="SIG002", platform_type="Scorpene-class Submarine",
                       fundamental_frequency=45, harmonics=[90, 135, 180],
                       description="Diesel-electric submarine, AIP mode, low-speed transit"),
        LofarSignature(id="SIG003", platform_type="Merchant Vessel (bulk carrier)",
                       fundamental_frequency=72, harmonics=[144],
                       description="Large single-screw merchant vessel, slow-speed"),
        LofarSignature(id="SIG004", platform_type="SSN Nuclear Submarine",
                       fundamental_frequency=42, harmonics=[84, 126, 168],
                       description="Nuclear submarine, reactor coolant pump tonal"),
        LofarSignature(id="SIG005", platform_type="Fishing Trawler",
                       fundamental_frequency=60, harmonics=[120, 180, 240],
                       description="Commercial fishing vessel with active trawl winch"),
    ]
    for sig in signatures:
        existing = db.query(LofarSignature).filter(LofarSignature.id == sig.id).first()
        if not existing:
            db.add(sig)
    db.commit()


def match_signature(detection: dict, db: Session) -> list[dict]:
    """Match a detection result against LOFAR signature database."""
    signatures = db.query(LofarSignature).all()
    matches = []

    det_fundamental = detection.get("fundamentalFrequency", 0)
    det_harmonics = set(detection.get("harmonics", []))

    for sig in signatures:
        score = 0.0

        # Fundamental frequency match
        freq_diff = abs(sig.fundamental_frequency - det_fundamental)
        if freq_diff == 0:
            score += 0.5
        elif freq_diff <= 3:
            score += 0.3
        elif freq_diff <= 6:
            score += 0.1

        # Harmonic pattern match
        sig_harmonics = set(sig.harmonics)
        if sig_harmonics and det_harmonics:
            overlap = len(sig_harmonics & det_harmonics)
            total = len(sig_harmonics | det_harmonics)
            harmonic_score = overlap / total if total > 0 else 0
            score += harmonic_score * 0.5

        if score > 0.1:
            matches.append({
                "signatureId": sig.id,
                "platformType": sig.platform_type,
                "confidence": round(score, 2),
                "fundamentalFrequency": sig.fundamental_frequency,
                "harmonics": sig.harmonics,
                "description": sig.description,
            })

    matches.sort(key=lambda m: m["confidence"], reverse=True)
    return matches


def store_match(sonobuoy_id: str, channel: int, signature_id: str,
                confidence: float, db: Session, timestamp: datetime | None = None):
    """Store a LOFAR match result."""
    m = LofarMatch(
        sonobuoy_id=sonobuoy_id,
        channel=channel,
        signature_id=signature_id,
        confidence=confidence,
        timestamp=timestamp or datetime.utcnow(),
    )
    db.add(m)
    db.commit()
    return m
