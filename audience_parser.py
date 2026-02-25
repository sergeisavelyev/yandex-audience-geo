import time
import csv
import json
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

REMOTE_DEBUGGING_PORT = 9222  # порт, на котором открыт Chrome с --remote-debugging-port
WAIT_SHORT = 0.3  # короткий таймаут для быстрого ожидания

def launch_chrome_with_debug():
    """Запускает Chrome с удаленной отладкой"""
    
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    # Запускаем Chrome с параметрами
    subprocess.Popen([
        chrome_path,
        f"--remote-debugging-port={REMOTE_DEBUGGING_PORT}",
        "--user-data-dir=C:/temp/chrome_debug_profile"  # отдельный профиль
    ])
    
    # Ждем пока Chrome запустится
    time.sleep(2)   
    print(f"✅ Chrome запущен на порту {REMOTE_DEBUGGING_PORT}")

def clean_percent(text):
    """Очищает процент от лишних символов, оставляет только число"""
    return text.replace("%", "").replace("\u2009", "").strip()

def connect_to_browser():
    options = Options()
    options.debugger_address = f"127.0.0.1:{REMOTE_DEBUGGING_PORT}"
    driver = webdriver.Chrome(options=options)
    return driver

def get_segments_table(driver):
    time.sleep(1)
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

    # --- Вкладка ОСНОВНОЕ ---
    main_tab_btn = WebDriverWait(driver, WAIT_SHORT).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Основное']"))
    )
    driver.execute_script("arguments[0].click();", main_tab_btn)

   # Ждем появления блока охвата
    reach_elem = WebDriverWait(driver, WAIT_SHORT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".audience-stats-widget-amount__percent"))
    )
    reach = reach_elem.text.strip()

    # --- Пол ---
    men = women = ""
    try:
        gender_cols = WebDriverWait(driver, WAIT_SHORT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".audience-stats-widget-gender__column"))
        )
        for col in gender_cols:
            label = col.find_element(By.CLASS_NAME, "audience-stats-widget-gender__label").text.lower()
            percent = col.find_element(By.CLASS_NAME, "audience-stats-widget-gender__value").text
            percent = clean_percent(percent)
            if "муж" in label:
                men = percent
            elif "жен" in label:
                women = percent
    except Exception as e:
        print(f"[!] Ошибка при парсинге пола: {e}")

    # --- Возраст ---
    age_data = {"<18":"", "18-25":"", "25-35":"", "35-45":"", "45-55":"", ">55":""}
    try:
        age_tspans = WebDriverWait(driver, WAIT_SHORT).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".audience-stats-widget-age .highcharts-data-labels tspan")
            )
        )
        labels = list(age_data.keys())
        for i, tspan in enumerate(age_tspans):
            if i >= len(labels):
                break
            age_data[labels[i]] = clean_percent(tspan.text)
    except Exception as e:
        print(f"[!] Ошибка при парсинге возраста: {e}")


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
    time.sleep(1.5)  # чтобы контент точно подгрузился

    # Находим все заголовки "Интересы"/"Категории"
    sections = driver.find_elements(By.CSS_SELECTOR, ".audience-segment-statistics__label_centered_yes")

    interests = []
    categories = []

    for section in sections:
        title = section.text.strip().lower()
        parent = section.find_element(By.XPATH, "./following-sibling::*[1]")
        rows = parent.find_elements(By.CSS_SELECTOR, ".audience-stats-widget-column-chart__affinity-row")

        data = [{"label": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__label").text,
                 "affinity": r.find_element(By.CLASS_NAME, "audience-stats-widget-column-chart__percent").text}
                for r in rows]

        if "интерес" in title:
            interests.extend(data)
        elif "категор" in title:
            categories.extend(data)

    return {
        "segment_id": segment_id,
        "reach": reach,
        "men": men,
        "women": women,
        **age_data,
        "cities": cities,
        "devices": devices,
        "interests": interests,
        "categories": categories
    }


def load_all_segments(driver):
    """Кликает 'Показать ещё' пока не исчезнет кнопка"""
    while True:
        try:
            show_more_btn = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.audience-segments-table__show-more-button")
                )
            )
            driver.execute_script("arguments[0].click();", show_more_btn)
            print("[↓] Нажали 'Показать ещё', ждём подгрузку...")
            time.sleep(0.5)
        except TimeoutException:
            print("[✓] Все сегменты подгружены, кнопка исчезла.")
            break
        except Exception as e:
            print(f"[!] Ошибка при клике на 'Показать ещё': {e}")
            break

# --- Вариант с плоскими таблицами ---
def save_flat_data(all_data):
    # Города
    with open("tables/source_table/segments_cities.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["segment_id", "city", "percent"])
        writer.writeheader()
        for item in all_data:
            for c in item["cities"]:
                writer.writerow({
                    "segment_id": item["segment_id"],
                    "city": c["city"],
                    "percent": c["percent"]
                })

    # Устройства
    with open("tables/source_table/segments_devices.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["segment_id", "device", "percent"])
        writer.writeheader()
        for item in all_data:
            for d in item["devices"]:
                writer.writerow({
                    "segment_id": item["segment_id"],
                    "device": d["device"],
                    "percent": d["percent"]
                })

    # Интересы
    with open("tables/source_table/segments_interests.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["segment_id", "label", "affinity"])
        writer.writeheader()
        for item in all_data:
            for a in item.get("interests", []):
                writer.writerow({
                    "segment_id": item["segment_id"],
                    "label": a["label"],
                    "affinity": a["affinity"]
                })

    # Категории
    with open("tables/source_table/segments_categories.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["segment_id", "label", "affinity"])
        writer.writeheader()
        for item in all_data:
            for a in item.get("categories", []):
                writer.writerow({
                    "segment_id": item["segment_id"],
                    "label": a["label"],
                    "affinity": a["affinity"]
                })

    # Демография (Основное)
    with open("tables/source_table/segments_demography.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "segment_id",
            "reach",
            "men",
            "women",
            "<18",
            "18-25",
            "25-35",
            "35-45",
            "45-55",
            ">55"
        ])
        writer.writeheader()

        for item in all_data:
            writer.writerow({
                "segment_id": item["segment_id"],
                "reach": item.get("reach"),
                "men": item.get("men"),
                "women": item.get("women"),
                "<18": item.get("<18"),
                "18-25": item.get("18-25"),
                "25-35": item.get("25-35"),
                "35-45": item.get("35-45"),
                "45-55": item.get("45-55"),
                ">55": item.get(">55")
            })       

    print("[✅] Все данные сохранены: segments_demography.csv, segments_cities.csv, segments_devices.csv, segments_interests.csv, segments_categories.csv")



def main():
    launch_chrome_with_debug()
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
    save_flat_data(all_data)

    print("Конец")

if __name__ == "__main__":
    main()
