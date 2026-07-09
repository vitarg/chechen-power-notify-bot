from __future__ import annotations

import re

from app.domain import MatchResult, NormalizedAddress, ParsedOutageSegment
from app.utils.text import comparable_name

STREET_MARKER_RE = re.compile(r"(?:\bулиц[аы]?\b|\bул\.|\bпер-ки\b|\bпер\.|\bпр\.|\bб-р\.?)", re.IGNORECASE)


def match_address_to_segment(
    address: NormalizedAddress,
    segment: ParsedOutageSegment,
) -> MatchResult:
    if not address.locality:
        return MatchResult(False, "address_has_no_locality")

    segment_locality = comparable_name(segment.locality)
    address_locality = comparable_name(address.locality)
    segment_landmarks = {comparable_name(landmark) for landmark in segment.landmarks}
    segment_landmarks.discard(None)
    segment_localities = {segment_locality, *segment_landmarks}
    segment_localities.discard(None)
    if segment_locality and address_locality not in segment_localities:
        return MatchResult(False, "locality_mismatch")

    if not segment_locality and segment.district:
        # District-only segments are intentionally not matched to a same-named city.
        return MatchResult(False, "district_without_locality")

    segment_streets = {comparable_name(street) for street in segment.streets}
    segment_streets.discard(None)
    if segment_streets:
        if address.street and comparable_name(address.street) in segment_streets:
            return MatchResult(True, "street_match", 1.0)
        if address.locality and comparable_name(address.locality) in segment_landmarks:
            return MatchResult(True, "landmark_match", 0.9)
        if address.landmark and comparable_name(address.landmark) in segment_streets | segment_landmarks:
            return MatchResult(True, "landmark_match", 0.9)
        return MatchResult(False, "street_mismatch")

    if segment_landmarks:
        if address.locality and comparable_name(address.locality) in segment_landmarks:
            return MatchResult(True, "landmark_match", 0.9)
        if address.landmark and comparable_name(address.landmark) in segment_landmarks:
            return MatchResult(True, "landmark_match", 0.9)
        if segment_locality and address_locality == segment_locality and not _is_parent_locality_segment(segment):
            return MatchResult(True, "locality_match", 0.8)
        return MatchResult(False, "landmark_mismatch")

    if STREET_MARKER_RE.search(segment.raw_zone):
        return MatchResult(False, "unparsed_street_segment")

    if segment_locality and address_locality == segment_locality:
        return MatchResult(True, "wide_locality_match", 0.7)

    return MatchResult(False, "no_rule_match")


def _is_parent_locality_segment(segment: ParsedOutageSegment) -> bool:
    return bool(segment.landmarks and segment.locality and "часть г." in segment.normalized_zone)
