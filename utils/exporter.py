"""
Exporter utility module
Handles saving Pandas DataFrames to CSV, JSON, or SQLite databases in the output directory.
"""

import os
import sqlite3
import pandas as pd
from typing import Optional, Union, Dict, Any

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

class DataExporter:
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        clean_cols = []
        for i, col in enumerate(df.columns):
            c_str = str(col).strip()
            if not c_str:
                c_str = f"column_{i+1}"
            # Replace invalid SQLite characters in column names
            c_str = c_str.replace(" ", "_").replace("/", "_").replace("-", "_")
            clean_cols.append(c_str)
        df.columns = clean_cols
        return df

    def export_csv(self, df: pd.DataFrame, filename: str) -> str:
        """Export dataframe to CSV."""
        if df.empty:
            print(f"[Exporter] Warning: DataFrame is empty, skipping CSV export for {filename}.")
            return ""
        df = self._clean_dataframe(df)
        if not filename.endswith(".csv"):
            filename += ".csv"
        filepath = os.path.join(self.output_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"[Exporter] Successfully saved {len(df)} rows to {filepath}")
        return filepath

    def export_json(self, df_or_dict: Union[pd.DataFrame, Dict[str, Any], list], filename: str) -> str:
        """Export dataframe or dictionary to JSON."""
        if not filename.endswith(".json"):
            filename += ".json"
        filepath = os.path.join(self.output_dir, filename)
        if isinstance(df_or_dict, pd.DataFrame):
            if df_or_dict.empty:
                print(f"[Exporter] Warning: DataFrame is empty, skipping JSON export for {filename}.")
                return ""
            df = self._clean_dataframe(df_or_dict)
            df.to_json(filepath, orient='records', indent=2)
        else:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(df_or_dict, f, indent=2)
        print(f"[Exporter] Successfully saved JSON to {filepath}")
        return filepath

    def export_sqlite(self, df: pd.DataFrame, table_name: str, db_name: str = "nba_data.db") -> str:
        """Export dataframe to SQLite table."""
        if df.empty:
            print(f"[Exporter] Warning: DataFrame is empty, skipping SQLite export for {table_name}.")
            return ""
        df = self._clean_dataframe(df)
        db_path = os.path.join(self.output_dir, db_name)
        with sqlite3.connect(db_path) as conn:
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"[Exporter] Successfully saved table '{table_name}' ({len(df)} rows) to {db_path}")
        return db_path
