from __future__ import annotations

from app.domain import MatchResult, NormalizedAddress, ParsedOutageSegment
from app.utils.text import comparable_name


def match_address_to_segment(
    address: NormalizedAddress,
    segment: ParsedOutageSegment,
) -> MatchResult:
    if not address.locality:
        return MatchResult(False, "address_has_no_locality")

    segment_locality = comparable_name(segment.locality)
    address_locality = comparable_name(address.locality)
    if segment_locality and address_locality != segment_locality:
        return MatchResult(False, "locality_mismatch")

    if not segment_locality and segment.district:
        # District-only segments are intentionally not matched to a same-named city.
        return MatchResult(False, "district_without_locality")

    segment_streets = {comparable_name(street) for street in segment.streets}
    segment_streets.discard(None)
    if segment_streets:
        if address.street and comparable_name(address.street) in segment_streets:
            return MatchResult(True, "street_match", 1.0)
        if address.landmark and comparable_name(address.landmark) in segment_streets:
            return MatchResult(True, "landmark_match", 0.9)
        return MatchResult(False, "street_mismatch")

    if segment_locality and address_locality == segment_locality:
        return MatchResult(True, "wide_locality_match", 0.7)

    return MatchResult(False, "no_rule_match")

