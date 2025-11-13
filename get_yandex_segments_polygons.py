import os
import requests
import pandas as pd
import json
import csv
import time
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("YANDEX_OAUTH_TOKEN")

URL = "https://api-audience.yandex.ru/v1/management/segments"

HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "Content-Type": "application/json"
}

def get_all_segments():
    all_segments = []
    offset = 0
    limit = 100

    while True:
        params = {"limit": limit, "offset": offset}
        response = requests.get(URL, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"[!] Ошибка {response.status_code}: {response.text}")
            break

        data = response.json()
        segments = data.get("segments", [])
        if not segments:
            break

        all_segments.extend(segments)
        print(f"[+] Получено сегментов: {len(all_segments)}")

        if len(segments) < limit:
            break

        offset += limit
        time.sleep(0.5)

    return all_segments


def extract_polygon(segment):
    form = segment.get("form")
    if form == "polygon" and segment.get("polygons"):
        poly_coords = []
        for poly in segment["polygons"]:
            points = []
            for p in poly.get("points", []):
                points.append([p["latitude"], p["longitude"]])

            # Замыкаем контур, если не замкнут
            if points[0] != points[-1]:
                points.append(points[0])

            poly_coords.append(points)
        return poly_coords

    elif form == "circle" and segment.get("circles"):
        # круги можно хранить как центр + радиус, но DataLens не умеет рисовать круги из центра
        c = segment["circles"][0]
        return [[[c["center"]["latitude"], c["center"]["longitude"]]]]  # хотя бы как точку

    return []


def save_to_csv(segments):
    with open("segments_polygons_bi.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["segment_id", "name", "form", "cookies", "polygon_json"])

        for s in segments:
            polygon = extract_polygon(s)
            if polygon:
                writer.writerow([
                    s["id"],
                    s["name"],
                    s["form"],
                    s.get("cookies_matched_quantity"),
                    json.dumps(polygon, ensure_ascii=False)
                ])

    print("[✅] Сохранено в segments_polygons_bi.csv")


def main():
    print("[*] Загружаем сегменты...")
    segments = get_all_segments()
    geo_segments = [s for s in segments if s.get("form") in ("polygon", "circle")]
    print(f"[+] Гео-сегментов: {len(geo_segments)}")
    save_to_csv(geo_segments)


if __name__ == "__main__":
    main()