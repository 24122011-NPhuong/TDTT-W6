import requests
import folium
from folium.plugins import Geocoder
from folium.features import DivIcon
from geopy.distance import geodesic
import math
from dotenv import load_dotenv
import os
load_dotenv()
OPENWEATHER_API_KEY = "YOUR_API_KEY"


def get_coordinates(city_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": city_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "CampusApp/1.0"}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    if not data:
        print("Không tìm thấy thành phố.")
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])


def get_weather(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }
    response = requests.get(url, params=params)
    data = response.json()
    return {
        "temp": data["main"]["temp"],
        "desc": data["weather"][0]["description"].capitalize(),
        "icon": data["weather"][0]["icon"]
    }
def get_top10_with_weather(places, center_lat, center_lon):
    places_sorted = sorted(places, key=lambda p: haversine(center_lat, center_lon, p["lat"], p["lon"]))
    top10 = places_sorted[:10]


    for p in top10:
        try:
            temp, cond, icon_url = get_weather(p["lat"], p["lon"])
            p["temperature"] = temp
            p["condition"]   = cond
            p["icon_url"]    = icon_url
        except:
            p["temperature"] = "N/A"
            p["condition"]   = "N/A"
            p["icon_url"]    = ""
    return top10


def get_nearby_places(lat, lon, radius=3000, label="park"):
    config = PLACE_CONFIG.get(label, ("leisure", label, "map-marker", "blue"))
    tag_key, tag_val = config[0], config[1]


    url = "https://overpass.kumi.systems/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
      way["{tag_key}"="{tag_val}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    try:
        response = requests.post(url, data={"data": query}, timeout=30)
        if not response.text.strip():
            print("Overpass API trả về rỗng.")
            return []
        data = response.json()
        places = []
        for element in data.get("elements", []):
            name = element.get("tags", {}).get("name", "")
            if not name:          
                continue
            p_lat = element.get("lat") or element.get("center", {}).get("lat")
            p_lon = element.get("lon") or element.get("center", {}).get("lon")
            if p_lat and p_lon:
                places.append({"name": name, "lat": p_lat, "lon": p_lon})
        return places
    except Exception as e:
        print(f"Lỗi Overpass API: {e}")
        return []




def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))




def print_result(city, lat, lon, temperature, condition, parks):
    print(f"\nCity: {city}")
    print(f"Coordinates: ({lat}, {lon})")
    print(f"Weather:")
    print(f"  - Temperature: {temperature}°C")
    print(f"  - Condition: {condition}")
    print(f"Nearby parks:")
    if not parks:
        print("Không tìm thấy công viên nào.")
    for i, p in enumerate(parks, 1):
        dist = haversine(lat, lon, p["lat"], p["lon"])
        print(f"  {i}. {p['name']} ({dist}m)")




def tao_ban_do_nghiep_vu_nhom(ten_tp, lat, lon, data_thoi_tiet, danh_sach_cong_vien):
    m = folium.Map(location=[lat, lon], zoom_start=15, tiles='CartoDB Positron')


    Geocoder(add_marker=True, position='topleft').add_to(m)


    folium.Circle(
        location=[lat, lon],
        radius=1000,
        color='#3498db',
        fill=True,
        fill_opacity=0.1,
        tooltip="Vùng tìm kiếm 1km"
    ).add_to(m)


    icon_url = f"https://openweathermap.org/img/wn/{data_thoi_tiet['icon']}@2x.png"
   
    folium.Marker(
        location=[lat, lon],
        icon=folium.CustomIcon(icon_url, icon_size=(60, 60)),
        tooltip=folium.Tooltip(
            f"<b>{ten_tp}</b><br>Tọa độ: {lat}, {lon}<br>Thời tiết: {data_thoi_tiet['desc']}",
            permanent=True,
            direction='bottom'
        )
    ).add_to(m)


    for cv in danh_sach_cong_vien:
        pos_cv = [cv['lat'], cv['lon']]
        khoang_cach = geodesic([lat, lon], pos_cv).kilometers
       
        folium.Marker(
            location=pos_cv,
            icon=folium.CustomIcon(icon_url, icon_size=(35, 35)),
            tooltip=f"Công viên: {cv['name']}"
        ).add_to(m)
       
        folium.Marker(
            location=pos_cv,
            icon=DivIcon(
                icon_size=(150,36),
                icon_anchor=(75, -10),
                html=f'<div style="font-size: 9pt; color: green; font-weight: bold; text-align: center;">{cv["name"]}</div>',
            )
        ).add_to(m)


        folium.PolyLine(
            locations=[[lat, lon], pos_cv],
            color="#e67e22",
            weight=2,
            dash_array='5, 5'
        ).add_to(m)


        mid_point = [(lat + cv['lat'])/2, (lon + cv['lon'])/2]
        folium.Marker(
            location=mid_point,
            icon=DivIcon(
                icon_size=(80, 20),
                html=f'<div style="font-size: 8pt; color: #e67e22; background: white; border: 1px solid; border-radius: 5px; text-align: center;">{khoang_cach:.2f} km</div>'
            )
        ).add_to(m)




    file_name = f"ket_qua_buoc5_{ten_tp.replace(' ', '_')}.html"
    m.save("output_map.html")
    return "output_map.html"


if __name__ == "__main__":
    load_dotenv()
    CITY_NAME = "Ho Chi Minh City"
    RADIUS = 3000
    PLACE_CONFIG = {
        "park":     ("leisure",  "park",     "leaf",        "green"),
        "museum":   ("tourism",  "museum",   "university",  "purple"),
        "school":   ("amenity",  "school",   "graduation-cap", "orange"),
        "cafe":     ("amenity",  "cafe",     "coffee",      "beige"),
        "hospital": ("amenity",  "hospital", "plus-sign",   "red"),
        "pharmacy": ("amenity",  "pharmacy", "heart",       "pink"),
    }
    LABEL = "park"


    print(" Đang lấy dữ liệu...")
    lat, lon = get_coordinates(CITY_NAME)
    weather = get_weather(lat, lon)
    places = get_nearby_places(lat, lon, RADIUS, LABEL)
    top10 = sorted(places, key=lambda p: haversine(lat, lon, p["lat"], p["lon"]))[:10]


    print(f"\nCity: {CITY_NAME}")
    print(f"Coordinates: ({lat}, {lon})")
    print(f"Weather:\n  - Temperature: {weather['temp']}°C\n  - Condition: {weather['desc']}")
    print("Nearby parks:")
    for i, p in enumerate(top10, 1):
        dist = haversine(lat, lon, p["lat"], p["lon"])
        print(f"  {i}. {p['name']} ({dist}m)")
    tao_ban_do_nghiep_vu_nhom(CITY_NAME, lat, lon, weather, top10)
    print("\n✅ Bản đồ đã lưu vào output_map.html")