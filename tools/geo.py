
import math, requests
POSTCODES_IO = "https://api.postcodes.io/postcodes"

def geocode_postcode(postcode: str):
    pc = postcode.replace(" ", "")
    r = requests.get(f"{POSTCODES_IO}/{pc}", timeout=15).json()
    if r.get("status") != 200 or not r.get("result"):
        return None
    res = r["result"]
    return res["latitude"], res["longitude"], res

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))
