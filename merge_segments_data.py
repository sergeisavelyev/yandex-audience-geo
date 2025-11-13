import pandas as pd
import json

df_data = pd.read_csv('segments_data.csv')
df_dpoly = pd.read_csv('segments_polygons_bi.csv')

merged_df = df_data.merge(df_dpoly, on="segment_id", how="inner")
merged_df.to_csv("segments_full.csv", index=False, encoding="utf-8")