# login_yandex_debug.py
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def main():
    # --- Настройки для подключения к уже запущенному Chrome ---
    options = Options()
    options.debugger_address = "127.0.0.1:9222"  # порт, на котором запущен Chrome с remote debugging

    print("[*] Подключаемся к уже открытому Chrome с включённой отладкой...")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # --- Переходим на страницу аудитории (если ещё не там) ---
        if "audience.yandex.ru" not in driver.current_url:
            print("[*] Открываем https://audience.yandex.ru/ ...")
            driver.get("https://audience.yandex.ru/")
            time.sleep(3)  # даём время на загрузку

        print("[*] Считываем содержимое страницы для парсера...")
        page_source = driver.page_source

        # --- Выводим базовую информацию для проверки ---
        print("[*] Заголовок страницы:", driver.title)
        print("[*] Текущий URL:", driver.current_url)
        print("[*] Длина контента:", len(page_source), "символов")
        print("[*] Браузер остаётся открытым для дальнейшего парсинга.")

        # --- Дополнительно можно искать элементы сегментов ---
        # Пример: получаем все кнопки детализации сегментов
        stats_buttons = driver.find_elements(By.CSS_SELECTOR, "span.audience-segment-row__stats-button")
        print(f"[*] Найдено {len(stats_buttons)} кнопок детализации сегментов.")

        # Тут можно дальше вызывать парсер или выводить содержимое сегментов
        input("Нажми Enter, когда закончишь работу с браузером...")

    finally:
        driver.quit()  # закрываем браузер после завершения работы

if __name__ == "__main__":
    main()
