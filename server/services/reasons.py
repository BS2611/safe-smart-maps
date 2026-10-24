"""Plain-language reasons for one segment (shown in the UI). Pure functions."""
from server.services.scoring import Evidence


def segment_reasons(ev: Evidence, factors: dict[str, float | None]) -> list[str]:
    reasons: list[str] = []
    if ev.open_weight_50m is None:
        reasons.append("not sure: open places data missing")
    else:
        count = round(ev.open_weight_50m)  # weight-based; approximate count for wording
        if ev.open_weight_50m > 0:
            reasons.append(f"{max(1, count)} open place{'s' if max(1, count) != 1 else ''} within 50 m")
        else:
            reasons.append("no open places nearby")
    if ev.lit is True:
        reasons.append("lit street")
    elif ev.lit is False:
        reasons.append("street not marked as lit")
    else:
        reasons.append("not sure: lighting data missing")
    if ev.outages_50m:
        reasons.append("streetlight outage reported nearby")
    if factors.get("main_road") is not None:
        main = factors["main_road"]
        reasons.append("main road" if main >= 100 else "side street" if main >= 50 else "alley or path")
    if ev.help_known and ev.help_distance_m is not None:
        reasons.append(f"help point {round(ev.help_distance_m)} m away")
    if ev.transit_active is True:
        reasons.append("transit running nearby")
    elif ev.transit_active is None:
        reasons.append("not sure: transit schedule not connected")
    if ev.tunnel:
        reasons.append("underpass or tunnel")
    if ev.turn_angle_deg >= 75:
        reasons.append("sharp turn")
    return reasons
