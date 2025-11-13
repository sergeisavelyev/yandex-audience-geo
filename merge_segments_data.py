import pandas as pd
import json

df_cat = pd.read_csv('segments_categories.csv')
df_int = pd.read_csv('segments_interests.csv')
df_dpoly = pd.read_csv('segments_polygons_bi.csv')

# Функция для преобразования процентов в числа
def convert_affinity(value):
    if isinstance(value, str):
        # Удаляем все нечисловые символы кроме точек и минусов
        cleaned = value.replace(' ', '').replace('%', '').replace(',', '.').strip()
        return float(cleaned)
    return float(value)

df_cat['affinity'] = df_cat['affinity'].apply(convert_affinity)
df_int['affinity'] = df_int['affinity'].apply(convert_affinity)


# Добавляем столбец с типом
df_cat['type'] = 'category'
df_int['type'] = 'interest'

# Объединяем в один датафрейм
df_all = pd.concat([df_cat, df_int], ignore_index=True)

# Мержим с полигонами
df_all = df_all.merge(df_dpoly, on='segment_id', how='left')

# Сохраняем
df_all.to_csv('segments_all.csv', index=False, encoding='utf-8')

# merged_df = df_cat.merge(df_dpoly, on="segment_id", how="left")
# merged_df['affinity'] = merged_df['affinity'].apply(convert_affinity)
# merged_df.to_csv("segments_full.csv", index=False, encoding="utf-8")