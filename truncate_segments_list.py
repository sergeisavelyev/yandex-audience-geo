import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("YANDEX_OAUTH_TOKEN")

HEADERS = {
    "Authorization": f"OAuth {TOKEN}",
    "Content-Type": "application/json"
}

URL_LIST = "https://api-audience.yandex.ru/v1/management/segments"


def get_all_segments():
    segments = []
    offset = 0
    limit = 100

    while True:
        resp = requests.get(
            URL_LIST,
            headers=HEADERS,
            params={"offset": offset, "limit": limit}
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Ошибка получения сегментов: {resp.status_code} {resp.text}"
            )

        data = resp.json()
        batch = data.get("segments", [])
        segments.extend(batch)

        if len(batch) < limit:
            break

        offset += limit

    return segments


# def delete_segment(segment_id):
#     resp = requests.delete(URL_DELETE.format(segment_id), headers=HEADERS)
#     return resp.status_code, resp.text


def delete_all_geo_segments():
    print("[*] Получаем список всех сегментов...")
    segments = get_all_segments()
    print(f"[+] Найдено сегментов всего: {len(segments)}")

    geo_segments = [
        s for s in segments
        if s.get("geo_segment_type") == "regular"
    ]

    total = len(geo_segments)
    print(f"[+] Geo-сегментов для удаления: {total}")

    deleted = 0

    for i, seg in enumerate(geo_segments, start=1):
        seg_id = seg["id"]
        status = seg.get("status")

        if status == "processing":
            print(f"[⏳] {i}/{total} Пропущен (обрабатывается): {seg_id}")
            continue

        url_delete = f"https://api-audience.yandex.ru/v1/management/segment/{seg_id}"
        r = requests.delete(url_delete, headers=HEADERS)

        if r.status_code == 204:
            print(f"[+] {i}/{total} Удалён: {seg_id}")
            deleted += 1

        elif r.status_code == 404:
            print(f"[!] {i}/{total} НЕ найден или нет прав: {seg_id}")

        else:
            print(f"[!] {i}/{total} - {r.status_code}: {r.text}")

        time.sleep(0.3)

    print(f"[✓] Удалено {deleted} из {total} geo-сегментов")

if __name__ == "__main__":
    delete_all_geo_segments()
