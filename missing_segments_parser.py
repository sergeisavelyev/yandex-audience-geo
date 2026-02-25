
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import subprocess
import time
import csv
import os

RETRIES = 2
REMOTE_DEBUGGING_PORT = 9222  # порт, на котором открыт Chrome с --remote-debugging-port
WAIT_SHORT = 0.3  # короткий таймаут для быстрого ожидания

# ---------------- CSV ID ----------------

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

def connect_to_browser():
    options = Options()
    options.debugger_address = f"127.0.0.1:{REMOTE_DEBUGGING_PORT}"
    driver = webdriver.Chrome(options=options)
    return driver

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

def clean_percent(text):
    """Очищает процент от лишних символов, оставляет только число"""
    return text.replace("%", "").replace("\u2009", "").strip()        

def get_all_segment_ids_from_polygons():
    file_path = "tables/source_table/segments_polygons_bi.csv"
    ids = set()

    if not os.path.exists(file_path):
        print("Нет файла")
        return ids

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.add(str(row["segment_id"]))

    print(f"[API] Всего ID из polygons: {len(ids)}")
    return ids


def get_parsed_segments_ids():
    file_path = "tables/source_table/segments_demography.csv"
    ids = set()

    if not os.path.exists(file_path):
        return ids

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.add(str(row["segment_id"]))

    print(f"[CSV] Уже спарсено: {len(ids)}")
    return ids


def get_missing_segment_ids():
    all_ids = get_all_segment_ids_from_polygons()
    parsed_ids = get_parsed_segments_ids()

    missing = all_ids - parsed_ids

    print(f"[MISSING] Осталось собрать: {len(missing)}")
    return missing


# ---------------- ERROR SAVE ----------------

def save_missing_segment(segment_id, error_text):
    file_path = "tables/source_table/segments_missing.csv"
    file_exists = os.path.exists(file_path)

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["segment_id", "error"])

        writer.writerow([segment_id, error_text])


# ---------------- RETRY ----------------

def with_retry(func, *args):
    for attempt in range(RETRIES):
        try:
            return func(*args)
        except (TimeoutException, StaleElementReferenceException) as e:
            print(f"[Retry {attempt+1}] {e}")
            time.sleep(2)

    raise Exception("Max retries exceeded")


# ---------------- ID FROM ROW ----------------

def extract_segment_id_from_row(row_elem):
    try:
        cells = row_elem.find_elements(By.CSS_SELECTOR, "td")
        if len(cells) > 5:
            return cells[5].text.strip()
    except Exception:
        pass
    return None

def collect_segment_data(driver, row_elem, segment_id):

    driver.execute_script(
        "arguments[0].click();",
        row_elem.find_elements(By.CSS_SELECTOR, "td")[-1].find_element(By.CSS_SELECTOR, "span")
    )

    main_tab_btn = WebDriverWait(driver, WAIT_SHORT).until(
        EC.element_to_be_clickable((By.XPATH, "//span[text()='Основное']"))
    )
    driver.execute_script("arguments[0].click();", main_tab_btn)

    reach_elem = WebDriverWait(driver, WAIT_SHORT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".audience-stats-widget-amount__percent"))
    )
    reach = reach_elem.text.strip()

    men = women = ""
    try:
        gender_cols = WebDriverWait(driver, WAIT_SHORT).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".audience-stats-widget-gender__column")
            )
        )
        for col in gender_cols:
            label = col.find_element(By.CLASS_NAME, "audience-stats-widget-gender__label").text.lower()
            percent = col.find_element(By.CLASS_NAME, "audience-stats-widget-gender__value").text
            percent = clean_percent(percent)

            if "муж" in label:
                men = percent
            elif "жен" in label:
                women = percent
    except:
        pass

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
    except:
        pass

    return {
        "segment_id": segment_id,
        "reach": reach,
        "men": men,
        "women": women,
        **age_data
    }

def save_flat_data(data_list):
    file_path = "tables/source_table/segments_missing.csv"
    file_exists = os.path.exists(file_path)

    fieldnames = [
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
    ]

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for row in data_list:
            writer.writerow(row)

# ---------------- MAIN ----------------

def main():

    launch_chrome_with_debug()
    driver = connect_to_browser()
    driver.get("https://audience.yandex.ru/")
    time.sleep(3)

    load_all_segments(driver)

    missing_ids = get_missing_segment_ids()

    rows = driver.find_elements(
        By.CSS_SELECTOR,
        "table.audience-segments-table__table tbody tr"
    )

    print(f"[UI] Найдено строк: {len(rows)}")

    all_data = []

    for i in range(len(rows)):

        # перечитываем DOM (защита от stale)
        rows = driver.find_elements(
            By.CSS_SELECTOR,
            "table.audience-segments-table__table tbody tr"
        )

        row = rows[i]
        segment_id = extract_segment_id_from_row(row)

        if not segment_id:
            continue

        if segment_id not in missing_ids:
            continue

        print(f"[START] {segment_id}")

        try:
            data = with_retry(collect_segment_data, driver, row, segment_id)
            all_data.append(data)
            print(f"[OK] {segment_id}")

        except Exception as e:
            print(f"[FAIL] {segment_id}")
            save_missing_segment(segment_id, str(e))

    # сохраняем одним вызовом
    if all_data:
        save_flat_data(all_data)

    print("DONE")


if __name__ == "__main__":
    main()