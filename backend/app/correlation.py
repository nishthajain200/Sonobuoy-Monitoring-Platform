"""Multi-sonobuoy correlation analysis."""
from sqlalchemy.orm import Session
from .models import Detection, Correlation
from datetime import datetime
from itertools import combinations


def correlate_sonobuoys(sonobuoy_ids: list[str], db: Session) -> list[dict]:
    """Correlate detections across multiple sonobuoys."""
    # Gather detections per sonobuoy
    detections_map: dict[str, list] = {}
    for sb_id in sonobuoy_ids:
        dets = db.query(Detection).filter(Detection.sonobuoy_id == sb_id).all()
        detections_map[sb_id] = dets

    results = []
    for sb_a, sb_b in combinations(sonobuoy_ids, 2):
        dets_a = detections_map.get(sb_a, [])
        dets_b = detections_map.get(sb_b, [])

        if not dets_a or not dets_b:
            score = 0.0
            common = []
        else:
            freqs_a = set()
            harmonics_a = set()
            for d in dets_a:
                freqs_a.add(d.fundamental_frequency)
                for h in (d.harmonics or []):
                    harmonics_a.add(h)

            freqs_b = set()
            harmonics_b = set()
            for d in dets_b:
                freqs_b.add(d.fundamental_frequency)
                for h in (d.harmonics or []):
                    harmonics_b.add(h)

            # Fundamental frequency overlap
            common_fund = freqs_a & freqs_b
            fund_score = len(common_fund) / max(1, len(freqs_a | freqs_b))

            # Harmonic overlap
            common_harm = harmonics_a & harmonics_b
            harm_score = len(common_harm) / max(1, len(harmonics_a | harmonics_b))

            score = round((fund_score * 0.5 + harm_score * 0.5) * 100, 1)
            common = sorted([int(f) for f in common_fund | common_harm])

        corr = Correlation(
            sonobuoy_id_a=sb_a,
            sonobuoy_id_b=sb_b,
            correlation_score=score,
            common_frequencies=common,
            timestamp=datetime.utcnow(),
        )
        db.add(corr)

        results.append({
            "sonobuoyA": sb_a,
            "sonobuoyB": sb_b,
            "correlationScore": score,
            "commonFrequencies": common,
        })

    db.commit()
    return results
