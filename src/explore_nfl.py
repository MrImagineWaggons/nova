import pandas as pd
import os

file_path = r"C:\Users\kovaa\OneDrive\Desktop\Nova - bot\data\nfl\spreadspoke.csv"
print("Exists?", os.path.exists(file_path))

df = pd.read_csv(file_path, encoding="utf-8-sig")
print(df.head())
print(df.columns)
