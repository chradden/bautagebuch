"""Reverse Geocoding via OpenStreetMap Nominatim API."""
import logging
import aiohttp

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


async def reverse_geocode(latitude: float, longitude: float) -> dict | None:
    """
    Wandelt GPS-Koordinaten in eine Adresse um.

    Returns:
        dict mit Schlüsseln: adresse, strasse, hausnummer, plz, ort, land
        oder None bei Fehler
    """
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "accept-language": "de",
    }
    headers = {
        "User-Agent": "Bautagebuch-Bot/1.0",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                NOMINATIM_URL, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    logger.error("Nominatim API Fehler: Status %s", resp.status)
                    return None

                data = await resp.json()

        address = data.get("address", {})

        strasse = address.get("road", "")
        hausnummer = address.get("house_number", "")
        plz = address.get("postcode", "")
        ort = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or ""
        )
        land = address.get("country", "")

        # Formatierte Adresse zusammenbauen
        teile = []
        if strasse:
            s = strasse
            if hausnummer:
                s += f" {hausnummer}"
            teile.append(s)
        if plz or ort:
            teile.append(f"{plz} {ort}".strip())
        if land:
            teile.append(land)

        adresse = ", ".join(teile) if teile else data.get("display_name", "")

        return {
            "adresse": adresse,
            "strasse": strasse,
            "hausnummer": hausnummer,
            "plz": plz,
            "ort": ort,
            "land": land,
            "display_name": data.get("display_name", ""),
        }

    except Exception as e:
        logger.error("Reverse Geocoding fehlgeschlagen: %s", e)
        return None
