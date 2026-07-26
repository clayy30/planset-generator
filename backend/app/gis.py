"""Public GIS lookup for planset title blocks.

Strategy (no paid tokens):
  1. ArcGIS World Geocoder → lat/lon, county (Subregion), ZIP+4, structure type
  2. FCC Census Area API → county FIPS / name (backup)
  3. County parcel FeatureServer / MapServer spatial query → PIN/APN, owner, acres, legal

County portals often rate-limit or hide behind tokens; we use published OpenData
endpoints (e.g. SAGIS for Chatham) and degrade gracefully when blocked.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

UA = "PlansetGenerator/1.3 (+https://github.com/clayy30/planset-generator; solar-permit-titleblock)"


@dataclass
class ParcelResult:
    matched_address: str = ""
    line1: str = ""
    city: str = ""
    state: str = "GA"
    zip: str = ""
    zip4: str = ""
    county: str = ""
    county_fips: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    apn: str = ""
    pin: str = ""
    owner: str = ""
    owner2: str = ""
    acres: Optional[float] = None
    legal_description: str = ""
    property_use: str = ""
    year_built: str = ""
    municipality: str = ""
    structure_type: str = ""
    source: str = ""
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("raw", None)
        return d


# Published open parcel services (extend as counties are validated)
PARCEL_LAYERS: list[dict[str, Any]] = [
    {
        "id": "chatham_sagis",
        "name": "Chatham / Savannah (SAGIS OpenData)",
        "counties": ["chatham"],
        "url": "https://pub.sagis.org/arcgis/rest/services/OpenData/Parcels/MapServer/27",
        "fields": {
            "apn": "PIN",
            "owner": "Owner",
            "owner2": "Owner2",
            "address": "PropAddress_Full",
            "city": "PropAddress_City",
            "zip": "PropAddress_Zip",
            "acres": "Acres",
            "legal": "Legal_Description",
            "use": "Property_Use",
            "year_built": "YearBuilt",
            "muni": "Municipality",
        },
    },
]


def _http_get_json(url: str, timeout: float = 12.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(str(e)) from e


def geocode_arcgis(single_line: str) -> ParcelResult:
    q = urllib.parse.urlencode(
        {
            "f": "json",
            "SingleLine": single_line,
            "outFields": "*",
            "maxLocations": 1,
            "forStorage": "false",
        }
    )
    url = f"https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates?{q}"
    data = _http_get_json(url)
    cands = data.get("candidates") or []
    if not cands:
        r = ParcelResult(warnings=["No geocode candidates"])
        return r
    c = cands[0]
    a = c.get("attributes") or {}
    loc = c.get("location") or {}
    r = ParcelResult(
        matched_address=c.get("address") or a.get("LongLabel") or single_line,
        line1=a.get("StAddr") or a.get("ShortLabel") or "",
        city=a.get("City") or "",
        state=a.get("RegionAbbr") or a.get("Region") or "GA",
        zip=str(a.get("Postal") or ""),
        zip4=str(a.get("PostalExt") or ""),
        county=(a.get("Subregion") or "").replace(" County", "") + (
            " County" if a.get("Subregion") and "County" not in str(a.get("Subregion")) else ""
        ),
        latitude=float(loc.get("y")) if loc.get("y") is not None else None,
        longitude=float(loc.get("x")) if loc.get("x") is not None else None,
        structure_type=str(a.get("StrucType") or a.get("StrucDet") or ""),
        source="ArcGIS World Geocoder",
        confidence=float(c.get("score") or 0) / 100.0,
        raw={"geocode": a},
    )
    if a.get("Subregion") and "County" not in r.county:
        r.county = f"{a['Subregion']}" if "County" in str(a["Subregion"]) else f"{a['Subregion']} County"
    return r


def enrich_fcc_county(result: ParcelResult) -> None:
    if result.latitude is None or result.longitude is None:
        return
    q = urllib.parse.urlencode(
        {"lat": result.latitude, "lon": result.longitude, "format": "json"}
    )
    try:
        data = _http_get_json(f"https://geo.fcc.gov/api/census/area?{q}", timeout=8)
        results = data.get("results") or []
        if results:
            r0 = results[0]
            result.county = r0.get("county_name") or result.county
            result.county_fips = r0.get("county_fips") or ""
            result.source = (result.source + " + FCC").strip(" +")
    except Exception as e:
        result.warnings.append(f"FCC county lookup failed: {e}")


def _parcel_spatial_query(layer_url: str, lon: float, lat: float) -> dict[str, Any] | None:
    q = urllib.parse.urlencode(
        {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }
    )
    data = _http_get_json(f"{layer_url}/query?{q}")
    feats = data.get("features") or []
    if not feats:
        return None
    return feats[0].get("attributes") or {}


def _parcel_address_query(
    layer_url: str, field: str, street: str, max_records: int = 5
) -> list[dict[str, Any]]:
    # extract house number + street token
    token = re.sub(r"[^A-Za-z0-9 ]", " ", street).upper().strip()
    parts = token.split()
    if len(parts) >= 2:
        # e.g. 30 HOUSTON
        like = f"%{parts[0]}%{parts[1]}%"
    else:
        like = f"%{token[:12]}%"
    where = f"UPPER({field}) LIKE '{like}'"
    q = urllib.parse.urlencode(
        {
            "where": where,
            "outFields": "*",
            "returnGeometry": "false",
            "resultRecordCount": str(max_records),
            "f": "json",
        }
    )
    try:
        data = _http_get_json(f"{layer_url}/query?{q}")
    except Exception:
        return []
    return [f.get("attributes") or {} for f in (data.get("features") or [])]


def apply_parcel_attrs(result: ParcelResult, attrs: dict[str, Any], fmap: dict[str, str], layer_name: str) -> None:
    def g(key: str) -> Any:
        fld = fmap.get(key)
        return attrs.get(fld) if fld else None

    pin = g("apn")
    if pin:
        result.apn = str(pin).strip()
        result.pin = result.apn
    own = g("owner")
    if own:
        result.owner = str(own).strip()
    own2 = g("owner2")
    if own2:
        result.owner2 = str(own2).strip()
    acres = g("acres")
    if acres is not None:
        try:
            result.acres = float(acres)
        except (TypeError, ValueError):
            pass
    legal = g("legal")
    if legal:
        result.legal_description = str(legal).strip()
    use = g("use")
    if use:
        result.property_use = str(use).strip()
    yb = g("year_built")
    if yb not in (None, ""):
        result.year_built = str(yb)
    muni = g("muni")
    if muni:
        result.municipality = str(muni).strip()
    addr = g("address")
    if addr and not result.line1:
        result.line1 = str(addr).title()
    city = g("city")
    if city:
        result.city = str(city).title()
    z = g("zip")
    if z:
        result.zip = str(z)[:5]
    result.source = f"{result.source} + {layer_name}".strip(" +")
    result.confidence = max(result.confidence, 0.92)
    result.raw["parcel"] = attrs


def lookup_parcel_layers(result: ParcelResult) -> None:
    if result.latitude is None or result.longitude is None:
        result.warnings.append("No coordinates for parcel spatial query")
        return
    county_key = (result.county or "").lower().replace(" county", "").strip()
    tried = 0
    for layer in PARCEL_LAYERS:
        counties = layer.get("counties") or []
        # Prefer matching county; still try SAGIS if county unknown and GA
        if counties and county_key and county_key not in counties:
            # still try if only one coastal layer and we're in GA
            if result.state.upper() not in ("GA", "GEORGIA"):
                continue
            if "chatham" not in counties:
                continue
            if county_key and county_key not in counties:
                continue
        tried += 1
        try:
            attrs = _parcel_spatial_query(layer["url"], result.longitude, result.latitude)
            if not attrs and result.line1:
                # fallback address filter on primary address field
                fmap = layer["fields"]
                addr_field = fmap.get("address")
                if addr_field:
                    cands = _parcel_address_query(layer["url"], addr_field, result.line1)
                    # pick best house-number match
                    hn = re.match(r"(\d+)", result.line1 or "")
                    if hn and cands:
                        for c in cands:
                            full = str(c.get(addr_field) or "")
                            if full.startswith(hn.group(1)):
                                attrs = c
                                break
                        if not attrs:
                            attrs = cands[0]
            if attrs:
                apply_parcel_attrs(result, attrs, layer["fields"], layer["name"])
                return
        except Exception as e:
            result.warnings.append(f"{layer['id']} blocked/failed: {e}")
    if tried and not result.apn:
        result.warnings.append(
            "Geocode OK but parcel PIN not found on open layers — enter APN manually or add county endpoint"
        )


def lookup_address(
    line1: str,
    city: str = "",
    state: str = "GA",
    zip_code: str = "",
) -> ParcelResult:
    single = ", ".join(x for x in [line1, city, f"{state} {zip_code}".strip()] if x)
    try:
        result = geocode_arcgis(single)
    except Exception as e:
        return ParcelResult(warnings=[f"Geocode blocked/failed: {e}"], line1=line1, city=city, state=state, zip=zip_code)

    if not result.line1:
        result.line1 = line1
    if city and not result.city:
        result.city = city
    if zip_code and not result.zip:
        result.zip = zip_code
    result.state = state or result.state

    try:
        enrich_fcc_county(result)
    except Exception as e:
        result.warnings.append(f"FCC: {e}")

    try:
        lookup_parcel_layers(result)
    except Exception as e:
        result.warnings.append(f"Parcel: {e}")

    return result


def apply_to_project_dict(project: dict[str, Any], parcel: ParcelResult) -> dict[str, Any]:
    """Merge GIS result into a project JSON-compatible dict."""
    meta = project.setdefault("meta", {})
    addr = meta.setdefault("address", {})
    if parcel.line1:
        addr["line1"] = parcel.line1
    if parcel.city:
        addr["city"] = parcel.city
    if parcel.state:
        addr["state"] = parcel.state if len(parcel.state) <= 2 else parcel.state[:2]
        if parcel.state.upper() in ("GEORGIA",):
            addr["state"] = "GA"
    if parcel.zip:
        addr["zip"] = parcel.zip
    if parcel.apn:
        addr["apn"] = parcel.apn
    if parcel.latitude is not None:
        addr["latitude"] = parcel.latitude
    if parcel.longitude is not None:
        addr["longitude"] = parcel.longitude
    # extended parcel fields on address + meta
    addr["county"] = parcel.county
    addr["owner_of_record"] = parcel.owner
    addr["acres"] = parcel.acres
    addr["legal_description"] = parcel.legal_description
    addr["property_use"] = parcel.property_use
    addr["year_built"] = parcel.year_built
    addr["zip4"] = parcel.zip4
    addr["structure_type"] = parcel.structure_type
    addr["gis_source"] = parcel.source
    if parcel.owner and not meta.get("customer_name"):
        meta["customer_name"] = parcel.owner.title()
    if parcel.county and not meta.get("ahj"):
        # reasonable default AHJ guess
        meta["ahj"] = parcel.county
    return project
