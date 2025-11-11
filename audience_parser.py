import time
import csv
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

REMOTE_DEBUGGING_PORT = 9222  # порт, на котором открыт Chrome с --remote-debugging-port
WAIT_SHORT = 3  # короткий таймаут для быстрого ожидания

def connect_to_browser():
    options = Options()
    options.debugger_address = f"127.0.0.1:{REMOTE_DEBUGGING_PORT}"
    driver = webdriver.Chrome(options=options)
    return driver

def get_segments_table(driver):
    time.sleep(2)
    try:
        table = driver.find_element(By.CSS_SELECTOR, "table.audience-segments-table__table")
    except Exception as e:
        print("[!] Таблица сегментов не найдена:", e)
        return [], []

    headers = [th.text.strip() for th in table.find_elements(By.CSS_SELECTOR, "thead th")]
    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
    segments = []
    for row in rows:
        cells = [td.text.strip() for td in row.find_elements(By.CSS_SELECTOR, "td")]
        segment_id = cells[5] if len(cells) > 5 else f"no_id_{rows.index(row)}"
        segments.append((row, cells, segment_id))
    return headers, segments

def collect_segment_data(driver, row_elem, segment_id):
    # Открываем детализацию
    driver.execute_script(
        "arguments[0].click();",
        row_elem.find_elements(By.CSS_SELECTOR, "td")[-1].find_element(By.CSS_SELECTOR, "span")
    )
    print(f"[*] Детализация сегмента {segment_id} открыта.")

    # --- Города и устройства ---
    cities_tab_btn = driver.find_element(By.XPATH, "//span[text()='Города и устройства']")
    driver.execute_script("arguments[0].click();", cities_tab_btn)

    cities_rows = WebDriverWait(driver, WAIT_SHORT).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, ".audience-segment-statistics__cities-devices-tab .audience-stats-widget-column-chart__chart-row_type_cities")
        )
    )
    cities = [{"city": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__label").text,
               "percent": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__percent").text}
              for r in cities_rows]

    devices_rows = WebDriverWait(driver, WAIT_SHORT).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, ".audience-segment-statistics__cities-devices-tab .audience-stats-widget-column-chart__chart-row_type_devices")
        )
    )
    devices = [{"device": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__label").text,
                "percent": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__percent").text}
               for r in devices_rows]

    # --- Интересы и категории ---
    interests_tab_btn = driver.find_element(By.XPATH, "//span[text()='Интересы и категории']")
    driver.execute_script("arguments[0].click();", interests_tab_btn)

    affinity_rows = WebDriverWait(driver, WAIT_SHORT).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".audience-stats-widget-column-chart__affinity-row"))
    )
    affinities = [{"label": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__label").text,
                   "affinity": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__percent").text}
                  for r in affinity_rows]

    return {
        "segment_id": segment_id,
        "cities": cities,
        "devices": devices,
        "affinities": affinities
    }

def load_all_segments(driver):
    """Кликает 'Показать ещё' пока не исчезнет кнопка"""
    while True:
        try:
            show_more_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.audience-segments-table__show-more-button")
                )
            )
            driver.execute_script("arguments[0].click();", show_more_btn)
            print("[↓] Нажали 'Показать ещё', ждём подгрузку...")
            time.sleep(2)
        except TimeoutException:
            print("[✓] Все сегменты подгружены, кнопка исчезла.")
            break
        except Exception as e:
            print(f"[!] Ошибка при клике на 'Показать ещё': {e}")
            break


def main():
    driver = connect_to_browser()
    driver.get("https://audience.yandex.ru/")
    print("[*] Подключились к браузеру и открыли аудитории.")
    time.sleep(3)  # ждём загрузку страницы и закрытие всплывашек вручную

    load_all_segments(driver) 

    headers, segments = get_segments_table(driver)
    print(f"[*] Заголовки: {headers}")
    print(f"[*] Найдено {len(segments)} сегментов.")

    all_data = []
    for row_elem, cells, segment_id in segments:
        if len(cells) > 4 and "готов" in cells[4].lower():
            try:
                data = collect_segment_data(driver, row_elem, segment_id)
                all_data.append(data)
            except TimeoutException:
                print(f"[!] Не удалось собрать данные сегмента {segment_id}")
            except Exception as e:
                print(f"[!] Ошибка сегмента {segment_id}: {e}")

    # Сохраняем в CSV
    with open("segments_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["segment_id", "cities", "devices", "affinities"])
        writer.writeheader()
        for item in all_data:
            writer.writerow({
                "segment_id": item["segment_id"],
                "cities": json.dumps(item["cities"], ensure_ascii=False),
                "devices": json.dumps(item["devices"], ensure_ascii=False),
                "affinities": json.dumps(item["affinities"], ensure_ascii=False)
            })

    print("[*] Данные всех сегментов сохранены в segments_data.csv")
    print("[*] Браузер остаётся открытым для дальнейшего анализа.")

if __name__ == "__main__":
    main()
