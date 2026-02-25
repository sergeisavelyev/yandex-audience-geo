import json
import csv
import folium
import h3
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union

# ------------------------------
# Настройки
# ------------------------------
H3_RESOLUTION = 9          # ~250 м
EXCLUDE_RATIO = 0.56       # если >56% площади гексагона попадает в исключения, удаляем
OUTPUT_FILE = "coords/hex_ids_coords.json"
CSV_FILE = "coords/coordinates_list.csv"
HEX_RADIUS = 1             # радиус гексагонов вокруг точки (количество колец H3)

# ------------------------------
# Загружаем исключающие зоны
# ------------------------------
exclude_file = "exclude_zones.geojson"
with open(exclude_file, "r", encoding="utf-8") as f:
    excl_gj = json.load(f)

exclude_polygons = [shape(f["geometry"]) for f in excl_gj["features"]]
exclude_union = unary_union(exclude_polygons)
print(f"[+] Исключающих зон: {len(exclude_polygons)}")

# ------------------------------
# Фильтрация гексагонов по исключающим зонам
# ------------------------------
def filter_hexes_by_exclude_ratio(hex_ids, exclude_union, max_ratio=EXCLUDE_RATIO):
    kept = []
    for hex_id in hex_ids:
        boundary = h3.cell_to_boundary(hex_id)  
        hex_poly = Polygon([(lon, lat) for lat, lon in boundary])
        overlap_area = hex_poly.intersection(exclude_union).area
        hex_area = hex_poly.area
        ratio = overlap_area / hex_area if hex_area > 0 else 0
        if ratio <= max_ratio:
            kept.append(hex_id)
    return kept

# ------------------------------
# Загружаем координаты
# ------------------------------
coordinates = []
with open(CSV_FILE, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        try:
            lat = float(row['lat'])
            lon = float(row['lon'])
            coordinates.append((lat, lon))
        except ValueError:
            continue

print(f"[+] Загружено координат: {len(coordinates)}")

# ------------------------------
# Генерация гексагонов вокруг каждой координаты
# ------------------------------
hex_ids = set()
for lat, lon in coordinates:
    center_hex = h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
    hexes_around = h3.grid_disk(center_hex, HEX_RADIUS)
    hex_ids.update(hexes_around)

print(f"[+] Всего гексагонов до фильтрации: {len(hex_ids)}")

# ------------------------------
# Фильтрация по исключающим зонам
# ------------------------------
hex_ids_filtered = filter_hexes_by_exclude_ratio(hex_ids, exclude_union)
print(f"[+] Гексагонов после фильтрации: {len(hex_ids_filtered)}")

# ------------------------------
# Визуализация
# ------------------------------
if coordinates:
    m = folium.Map(location=[coordinates[0][0], coordinates[0][1]], zoom_start=13, tiles="CartoDB positron")
else:
    m = folium.Map(location=[55.79, 49.12], zoom_start=13, tiles="CartoDB positron")

# Исключающие зоны
folium.GeoJson(excl_gj, name="Исключённые зоны", style_function=lambda x: {
    "fill": True, "color": "cyan", "fillOpacity": 0.4, "weight": 1
}).add_to(m)

# Гексагоны
layer_hex = folium.FeatureGroup(name="H3 гексагоны вокруг координат", show=True)
for hex_id in hex_ids_filtered:
    boundary = h3.cell_to_boundary(hex_id)
    folium.Polygon(
        locations=[(lat, lon) for lat, lon in boundary],
        color="red", weight=1, fill=True, fill_opacity=0.35
    ).add_to(layer_hex)
layer_hex.add_to(m)

# Координаты точек
for lat, lon in coordinates:
    folium.CircleMarker(location=(lat, lon), radius=2, color="blue", fill=True, fill_opacity=0.7).add_to(m)

# Слой управления
folium.LayerControl(collapsed=False).add_to(m)

# Сохраняем карту
m.save("maps/hex_around_coords.html")
print("[+] Карта сохранена: maps/hex_around_coords.html")

# ------------------------------
# Сохраняем массив в файл
# ------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(list(hex_ids_filtered), f, ensure_ascii=False, indent=2)

print(f"[+] Список H3-гексагонов сохранён в {OUTPUT_FILE}")