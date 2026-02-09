import json
import folium
import h3
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union

# ------------------------------
# Настройки
# ------------------------------
H3_RESOLUTION = 9          # ~250 м
EXCLUDE_RATIO = 0.56       # если >56% площади гексагона попадает в исключения, удаляем
MIN_POLY_POINTS = 3        # минимальное количество точек для LatLngPoly
OUTPUT_FILE = "hex_ids.json"

# ------------------------------
# Загружаем исключающие зоны (озера, реки и т.д.)
# ------------------------------
exclude_file = "exclude_zones.geojson"
with open(exclude_file, "r", encoding="utf-8") as f:
    excl_gj = json.load(f)

exclude_polygons = [shape(f["geometry"]) for f in excl_gj["features"]]
exclude_union = unary_union(exclude_polygons)
print(f"[+] Исключающих зон: {len(exclude_polygons)}")

# ------------------------------
# Загружаем границы города
# ------------------------------
geojson_file = "kazan_map.geojson"
with open(geojson_file, "r", encoding="utf-8") as f:
    gj = json.load(f)

city_polygon = shape(gj['features'][0]['geometry'])
print("[+] Границы города загружены")

# ------------------------------
# Shapely → H3 LatLngPoly с защитой от маленьких полигонов
# ------------------------------
def shapely_to_latlngpoly(geom, min_points=3):
    """
    Преобразует Shapely Polygon / MultiPolygon в H3 LatLngPoly.
    Отбрасывает полигоны и внутренние кольца с < min_points точек.
    """
    polys = []
    if geom.is_empty:
        return polys

    if geom.geom_type == "Polygon":
        geom = [geom]
    elif geom.geom_type == "MultiPolygon":
        geom = list(geom.geoms)

    for poly in geom:
        if poly.exterior is None or len(poly.exterior.coords) < min_points:
            continue

        outer = [(lat, lon) for lon, lat in poly.exterior.coords]

        # исправлено: если дыр нет — передаем пустой список
        holes = []
        for ring in poly.interiors:
            if ring is not None and len(ring.coords) >= min_points:
                holes.append([(lat, lon) for lon, lat in ring.coords])

        polys.append(h3.LatLngPoly(outer, holes))  # holes всегда список, не None

    return polys


latlng_polys = shapely_to_latlngpoly(city_polygon)
if not latlng_polys:
    raise ValueError("Нет допустимых полигонов для H3 после вырезания исключающих зон!")

# ------------------------------
# Генерация всех H3-гексагонов по городу
# ------------------------------
hex_ids = set()
for poly in latlng_polys:
    hex_ids.update(h3.polygon_to_cells(poly, H3_RESOLUTION))
hex_ids = list(hex_ids)
print(f"[+] Всего гексагонов по городу: {len(hex_ids)}")

# ------------------------------
# Фильтрация гексагонов по исключающим зонам (>56% площади)
# ------------------------------
def filter_hexes_by_exclude_ratio(hex_ids, exclude_union, max_ratio=EXCLUDE_RATIO):
    kept = []
    for hex_id in hex_ids:
        boundary = h3.cell_to_boundary(hex_id)  # [(lat, lon)]
        hex_poly = Polygon([(lon, lat) for lat, lon in boundary])
        overlap_area = hex_poly.intersection(exclude_union).area
        hex_area = hex_poly.area
        ratio = overlap_area / hex_area if hex_area > 0 else 0
        if ratio <= max_ratio:
            kept.append(hex_id)
    return kept

hex_ids_filtered = filter_hexes_by_exclude_ratio(hex_ids, exclude_union)
print(f"[+] Гексагонов после фильтрации по исключениям: {len(hex_ids_filtered)}")

# ------------------------------
# Визуализация
# ------------------------------
m = folium.Map(location=[55.79, 49.12], zoom_start=11, tiles="CartoDB positron")

# Город
folium.GeoJson(gj, name="Город", style_function=lambda x: {
    "fill": False, "color": "blue", "weight": 2
}).add_to(m)

# Исключающие зоны
folium.GeoJson(excl_gj, name="Исключённые зоны", style_function=lambda x: {
    "fill": True, "color": "cyan", "fillOpacity": 0.4, "weight": 1
}).add_to(m)

# Гексагоны (до фильтрации серые)
layer_before = folium.FeatureGroup(name="До фильтрации", show=False)
for hex_id in hex_ids:
    boundary = h3.cell_to_boundary(hex_id)
    folium.Polygon(
        locations=[(lat, lon) for lat, lon in boundary],
        color="gray", weight=1, fill=True, fill_opacity=0.15
    ).add_to(layer_before)
layer_before.add_to(m)

# Гексагоны (после фильтрации красные)
layer_after = folium.FeatureGroup(name="После фильтрации", show=True)
for hex_id in hex_ids_filtered:
    boundary = h3.cell_to_boundary(hex_id)
    folium.Polygon(
        locations=[(lat, lon) for lat, lon in boundary],
        color="red", weight=1, fill=True, fill_opacity=0.35
    ).add_to(layer_after)
layer_after.add_to(m)

# Слой управления
folium.LayerControl(collapsed=False).add_to(m)

# Сохраняем карту
m.save("hex_with_exclusions_56.html")
print("[+] Карта сохранена: hex_with_exclusions.html")



# ------------------------------
# Сохраняем массив в файл
# ------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(hex_ids_filtered, f, ensure_ascii=False, indent=2)

print(f"[+] Список H3-гексагонов сохранён в {OUTPUT_FILE}")