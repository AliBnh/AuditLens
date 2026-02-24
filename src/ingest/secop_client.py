# src/ingest/secop_client.py
"""
SECOP II API client.
Pulls contract data from Colombia's open procurement platform,
saves to Parquet for all downstream work.
"""

import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from tqdm import tqdm
import sys

# Add project root to path so config is importable
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import (
    SECOP_ENDPOINT, API_PAGE_SIZE, DATA_RAW,
    TRAIN_START, VALID_END
)

# ── Columns we actually need ────────────────────────────────────────────────
COLUMNS = [
    "id_contrato",
    "codigo_entidad",
    "nit_entidad",
    "nombre_entidad",
    "departamento",
    "ciudad",
    "orden",
    "sector",
    "rama",
    "codigo_proveedor",
    "documento_proveedor",
    "proveedor_adjudicado",
    "modalidad_de_contratacion",
    "tipo_de_contrato",
    "estado_contrato",
    "codigo_de_categoria_principal",
    "descripcion_del_proceso",
    "objeto_del_contrato",
    "fecha_de_firma",
    "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato",
    "valor_del_contrato",
    "dias_adicionados",
    "destino_gasto",
    "origen_de_los_recursos",
    "espostconflicto",
    "es_pyme",
    "duraci_n_del_contrato",
]

# ── Date columns to parse ───────────────────────────────────────────────────
DATE_COLS = [
    "fecha_de_firma",
    "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato",
]


def fetch_page(offset: int, limit: int) -> list[dict]:
    """Pull one page from the API."""
    params = {
        "$select": ",".join(COLUMNS),
        "$where": (
            f"fecha_de_inicio_del_contrato >= '{TRAIN_START}T00:00:00' "
            f"AND fecha_de_inicio_del_contrato <= '{VALID_END}T23:59:59' "
            f"AND valor_del_contrato > '0'"
        ),
        "$limit": limit,
        "$offset": offset,
        "$order": "fecha_de_inicio_del_contrato ASC",
    }
    response = requests.get(SECOP_ENDPOINT, params=params, timeout=120)
    response.raise_for_status()
    return response.json()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply types and basic cleaning."""
    # Numeric
    df["valor_del_contrato"] = pd.to_numeric(df["valor_del_contrato"], errors="coerce")
    df["dias_adicionados"] = pd.to_numeric(df["dias_adicionados"], errors="coerce").fillna(0)

    # Dates
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

    # Drop rows with no contract value or no start date
    df = df.dropna(subset=["valor_del_contrato", "fecha_de_inicio_del_contrato"])

    # Drop zero or negative values
    df = df[df["valor_del_contrato"] > 0]

    return df.reset_index(drop=True)


def pull_data(max_rows: int = None, output_filename: str = "secop_raw.parquet") -> Path:
    """
    Main pull function.
    
    Args:
        max_rows: If set, stops after this many rows. Use 1000 for testing.
        output_filename: Parquet filename saved to data/raw/
    
    Returns:
        Path to saved parquet file.
    """
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    output_path = DATA_RAW / output_filename

    chunks = []
    offset = 0
    total_fetched = 0

    print(f"Starting pull from SECOP II API...")
    print(f"Date range: {TRAIN_START} → {VALID_END}")
    print(f"Max rows: {'unlimited' if max_rows is None else f'{max_rows:,}'}")    
    print("-" * 50)

    while True:
        limit = API_PAGE_SIZE
        if max_rows is not None:
            limit = min(API_PAGE_SIZE, max_rows - total_fetched)
            if limit <= 0:
                break

        try:
            batch = fetch_page(offset=offset, limit=limit)
        except requests.exceptions.RequestException as e:
            print(f"\n❌ API error at offset {offset:,}: {e}")
            break

        if not batch:
            break

        chunks.append(pd.DataFrame(batch))
        total_fetched += len(batch)
        offset += len(batch)

        print(f"  ✓ Fetched {total_fetched:,} rows so far...")

        if len(batch) < limit:
            # Last page
            break

    if not chunks:
        print("❌ No data fetched. Check your API connection.")
        return None

    print(f"\nCombining {len(chunks)} chunks...")
    df = pd.concat(chunks, ignore_index=True)

    print("Cleaning data...")
    df = clean_dataframe(df)

    print(f"Saving to {output_path}...")
    df.to_parquet(output_path, index=False, compression="snappy")

    # Summary
    print("\n" + "=" * 50)
    print("✅ PULL COMPLETE")
    print(f"   Rows saved:      {len(df):,}")
    print(f"   Columns:         {len(df.columns)}")
    print(f"   Date range:      {df['fecha_de_inicio_del_contrato'].min().date()} → {df['fecha_de_inicio_del_contrato'].max().date()}")
    print(f"   File size:       {output_path.stat().st_size / 1e6:.1f} MB")
    print(f"   Saved to:        {output_path}")
    print("=" * 50)

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pull SECOP II contract data")
    parser.add_argument("--test", action="store_true", help="Pull only 1000 rows for testing")
    parser.add_argument("--max-rows", type=int, default=None, help="Limit total rows pulled")
    args = parser.parse_args()

    if args.test:
        pull_data(max_rows=1000, output_filename="secop_test.parquet")
    else:
        pull_data(max_rows=args.max_rows, output_filename="secop_raw.parquet")