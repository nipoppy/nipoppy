"""
CLIENT-SIDE: Geographic location tracking

Handles GeoIP lookup and country code management.
This is SEPARATE from command tracking - location is an additional feature.

Functions:
- get_user_country(): Lookup country via GeoIP (called once during init)
- get_country_from_config(): Read cached country from dataset config
- save_country_to_config(): Store country in dataset config
- record_location(): Record location metric (separate from commands)
"""

import os
from pathlib import Path
from typing import Optional

try:
    import geoip2.database
    import requests
    _GEOIP_AVAILABLE = True
except ImportError:
    _GEOIP_AVAILABLE = False


def get_user_country() -> str:
    """
    CLIENT-SIDE: Get user's country from IP address

    Makes external API calls:
    1. ipify.org - Get public IP address
    2. GeoIP database - Lookup country from IP

    NOTE: This is only called ONCE during dataset initialization.
    Subsequent commands read from config (see get_country_from_config).

    Returns:
        Two-letter ISO country code (e.g., "US", "CA", "IN") or "UNKNOWN"
    """
    if not _GEOIP_AVAILABLE:
        return "UNKNOWN"

    try:
        # === PRESENTATION MARKER: Get Public IP ===
        ip = requests.get('https://api.ipify.org', timeout=2).text

        # === PRESENTATION MARKER: GeoIP Lookup ===
        db_path = os.getenv(
            'GEOIP_DB_PATH',
            '/usr/share/GeoIP/GeoLite2-Country.mmdb'  # Standard location
        )

        with geoip2.database.Reader(db_path) as reader:
            response = reader.country(ip)
            return response.country.iso_code

    except Exception:
        # Fail gracefully - no internet, no DB, etc.
        return "UNKNOWN"


def get_country_from_config(params: dict) -> str:
    """
    CLIENT-SIDE: Get cached country code from dataset config

    Reads from CUSTOM.TELEMETRY.COUNTRY_CODE in global_config.json.
    This avoids repeated GeoIP lookups on every command.

    Args:
        params: Command parameters (should contain 'dpath_root')

    Returns:
        Country code from config, or "UNKNOWN" if not available
    """
    try:
        from nipoppy.config.main import Config

        # Extract dataset path
        dataset_path = params.get("dpath_root")
        if not dataset_path:
            return "UNKNOWN"

        # Load config
        config_path = Path(dataset_path) / "global_config.json"
        if not config_path.exists():
            return "UNKNOWN"

        config = Config.load(config_path)
        country_code = config.get_telemetry_country_code()

        return country_code if country_code else "UNKNOWN"

    except Exception:
        return "UNKNOWN"


def save_country_to_config(params: dict) -> None:
    """
    CLIENT-SIDE: Save country code to dataset config

    Called once after dataset initialization.
    Stores GeoIP result in CUSTOM.TELEMETRY.COUNTRY_CODE.

    Args:
        params: Command parameters (should contain 'dpath_root')
    """
    try:
        from nipoppy.config.main import Config

        # Get dataset path
        dataset_path = params.get("dpath_root")
        if not dataset_path:
            return

        config_path = Path(dataset_path) / "global_config.json"
        if not config_path.exists():
            return

        # Load config
        config = Config.load(config_path)

        # === PRESENTATION MARKER: GeoIP Lookup (ONE TIME ONLY) ===
        country_code = get_user_country()

        # Save to config
        config.set_telemetry_preferences(
            country_code=country_code,
            send_telemetry=True
        )
        config.save(config_path)

        print(f"✓ Location saved: {country_code}")

    except Exception as e:
        print(f"⚠ Warning: Could not save location: {e}")


def record_location(params: dict) -> None:
    """
    CLIENT-SIDE: Record location metric (separate from command tracking)

    This function updates the location_by_country metric.
    Called after dataset initialization to record where the installation is.

    Args:
        params: Command parameters (should contain 'dpath_root')
    """
    from nipoppy.telemetry.metrics import get_metrics

    try:
        metrics = get_metrics()
        if metrics and "location_by_country" in metrics:
            # Get country from config
            country_code = get_country_from_config(params)

            # === PRESENTATION MARKER: Record Location Metric ===
            # This is SEPARATE from command tracking - it's an additional feature
            metrics["location_by_country"].add(
                1,
                attributes={"country": country_code}
            )
    except Exception:
        # Silent failure - never crash user's command
        pass
