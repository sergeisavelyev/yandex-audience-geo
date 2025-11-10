import os
import requests
from dotenv import load_dotenv
import json
import time
import requests
from shapely.geometry import shape, Polygon, box

load_dotenv()

token = os.getenv("YANDEX_OAUTH_TOKEN")

# ------------------------------
# Настройки API
# ------------------------------

headers = {
    "Authorization": f"OAuth {token}",
    "Content-Type": "application/json"
}
url_create = "https://api-audience.yandex.ru/v1/management/segments/create_geo_polygon"

# ------------------------------
# Загружаем границы города
# ------------------------------
geojson_file = "kazan_map.geojson"
with open(geojson_file, "r", encoding="utf-8") as f:
    gj = json.load(f)

city_polygon = shape(gj['features'][0]['geometry'])
print("[+] Границы города загружены")

# ------------------------------
# Генерируем сетку 500x500 м (~0.0045 градуса)
# ------------------------------
delta = 0.0045  # ~500 м
minx, miny, maxx, maxy = city_polygon.bounds

all_polygons = []
lat = miny
while lat < maxy:
    lon = minx
    while lon < maxx:
        square = box(lon, lat, lon + delta, lat + delta)
        if city_polygon.intersects(square):
            coords = [
                {"latitude": lat, "longitude": lon},
                {"latitude": lat + delta, "longitude": lon},
                {"latitude": lat + delta, "longitude": lon + delta},
                {"latitude": lat, "longitude": lon + delta},
                {"latitude": lat, "longitude": lon}
            ]
            all_polygons.append({"points": coords})
        lon += delta
    lat += delta

print(f"[+] Сетка готова: {len(all_polygons)} квадратов внутри города")

# ------------------------------
# Загружаем прогресс
# ------------------------------
try:
    with open("progress.json", "r", encoding="utf-8") as f:
        progress = json.load(f)
except FileNotFoundError:
    progress = {"last_created_index": -1, "created_segments": []}

start_idx = progress["last_created_index"] + 1

# ------------------------------
# Создаём сегменты через API
# ------------------------------
for idx, polygon in enumerate(all_polygons[start_idx:], start=start_idx):
    payload = {
        "segment": {
            "name": f"Kazan Segment {idx+1}",
            "geo_segment_type": "regular",
            "polygons": [polygon]
        }
    }

    try:
        response = requests.post(url_create, headers=headers, json=payload)
        data = response.json()
    except Exception as e:
        print(f"[!] Ошибка запроса для сегмента {idx+1}:", e)
        break

    if response.status_code == 200:
        seg_id = data['segment']['id']
        print(f"[+] Сегмент {idx+1} создан, ID: {seg_id}")
        progress["last_created_index"] = idx
        progress["created_segments"].append({"id": seg_id, "polygon": polygon})
        with open("progress.json", "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        time.sleep(1)  # пауза для API
    else:
        print(f"[!] Ошибка при создании сегмента {idx+1}: {response.status_code} {data}")
        break

print("[*] Скрипт завершён, прогресс сохранён в progress.json")
