import pandas as pd
import json

df_cat = pd.read_csv('tables/source_table/segments_categories.csv')
df_int = pd.read_csv('tables/source_table/segments_interests.csv')
df_cities = pd.read_csv('tables/source_table/segments_cities.csv')
df_devices = pd.read_csv('tables/source_table/segments_devices.csv')
df_base = pd.read_csv('tables/source_table/segments_polygons_bi.csv')

# Функция для преобразования процентов в числа
def convert_affinity(value):
    if isinstance(value, str):
        # Удаляем все нечисловые символы кроме точек и минусов
        cleaned = value.replace(' ', '').replace('%', '').replace(',', '.').strip()
        return float(cleaned)
    return float(value)

df_cat['affinity'] = df_cat['affinity'].apply(convert_affinity)
df_int['affinity'] = df_int['affinity'].apply(convert_affinity)
df_cities['percent'] = df_cities['percent'].apply(convert_affinity)
df_devices['percent'] = df_devices['percent'].apply(convert_affinity)

# Добавляем столбец с типом
df_cat['type'] = 'category'
df_int['type'] = 'interest'
df_cities['type'] = 'city'
df_devices['type'] = 'device'

df_cat = df_cat.merge(df_base, on='segment_id', how='left').to_csv('tables/prepared/segments_categories.csv', index=False, encoding='utf-8')
df_int = df_int.merge(df_base, on='segment_id', how='left').to_csv('tables/prepared/segments_interests.csv', index=False, encoding='utf-8')
df_cities = df_cities.merge(df_base, on='segment_id', how='left').to_csv('tables/prepared/segments_cities.csv', index=False, encoding='utf-8')
df_devices = df_devices.merge(df_base, on='segment_id', how='left').to_csv('tables/prepared/segments_devices.csv', index=False, encoding='utf-8')




# Вариант обьединения в одно

# # Объединяем в один датафрейм
# df_all = pd.concat([df_cat, df_int], ignore_index=True)

# # Мержим с полигонами
# df_all = df_all.merge(df_base, on='segment_id', how='left')

# # Сохраняем
# df_all.to_csv('segments_all.csv', index=False, encoding='utf-8')

# merged_df = df_cat.merge(df_base, on="segment_id", how="left")
# merged_df['affinity'] = merged_df['affinity'].apply(convert_affinity)
# merged_df.to_csv("segments_full.csv", index=False, encoding="utf-8")
