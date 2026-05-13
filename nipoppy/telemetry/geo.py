"""
Geographic location tracking.

Performs a GeoIP lookup and records the country code as a telemetry metric.
"""

import httpx


def get_user_country() -> str:
    """
    Get the user's country code from their public IP address.

    Returns a two-letter ISO country code (e.g. "US", "CA", "IN") or
    "UNKNOWN" on any failure.
    """
    try:
        ip_response = httpx.get('https://api.ipify.org', timeout=5)
        ip_response.raise_for_status()
        public_ip = ip_response.text.strip()

        response = httpx.get(f'https://api.db-ip.com/v2/free/{public_ip}', timeout=5)
        response.raise_for_status()
        data = response.json()

        country_code = data.get('countryCode')
        if country_code and isinstance(country_code, str) and len(country_code) == 2:
            return country_code.upper()

        return "UNKNOWN"

    except Exception:
        return "UNKNOWN"


def record_location() -> None:
    """
    Perform a GeoIP lookup and record the location metric.

    Called once during `nipoppy init`.
    """
    from nipoppy.telemetry.metrics import get_metrics

    try:
        metrics = get_metrics()
        if metrics and "location_by_country" in metrics:
            country_code = get_user_country()
            metrics["location_by_country"].add(
                1,
                attributes={"country": country_code}
            )
    except Exception:
        pass
