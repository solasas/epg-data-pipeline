"""Load cleaned channels/programmes DataFrames into PostgreSQL using upsert."""
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values

from db.connection import get_connection
from parse import parse_epg
from transform import transform

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

CHANNELS_UPSERT_SQL = """
    INSERT INTO channels (channel_id, display_name)
    VALUES %s
    ON CONFLICT (channel_id) DO UPDATE SET
        display_name = EXCLUDED.display_name
    RETURNING (xmax = 0) AS inserted
"""

PROGRAMMES_UPSERT_SQL = """
    INSERT INTO programmes (
        channel_id, start_time, stop_time, title,
        description, category, duration_minutes, ingested_at
    )
    VALUES %s
    ON CONFLICT (channel_id, start_time) DO UPDATE SET
        stop_time = EXCLUDED.stop_time,
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        category = EXCLUDED.category,
        duration_minutes = EXCLUDED.duration_minutes,
        ingested_at = EXCLUDED.ingested_at
    RETURNING (xmax = 0) AS inserted
"""


def create_tables(conn):
    schema_sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()


def _channel_rows(channels_df):
    return list(channels_df[["channel_id", "display_name"]].itertuples(index=False, name=None))


def _programme_rows(programmes_df):
    rows = []
    for row in programmes_df.itertuples(index=False):
        duration = int(row.duration_minutes) if pd.notnull(row.duration_minutes) else None
        rows.append((
            row.channel_id, row.start, row.stop, row.title,
            row.description, row.category, duration, row.ingested_at,
        ))
    return rows


def _run_upsert(conn, query, rows):
    with conn.cursor() as cur:
        results = execute_values(cur, query, rows, fetch=True)
    conn.commit()
    inserted = sum(1 for r in results if r["inserted"])
    updated = len(results) - inserted
    return inserted, updated


def upsert_channels(conn, channels_df):
    return _run_upsert(conn, CHANNELS_UPSERT_SQL, _channel_rows(channels_df))


def upsert_programmes(conn, programmes_df):
    return _run_upsert(conn, PROGRAMMES_UPSERT_SQL, _programme_rows(programmes_df))


def verify(conn):
    print("\n--- Sample channels ---")
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM channels ORDER BY channel_id LIMIT 5")
        for row in cur.fetchall():
            print(dict(row))

    print("\n--- Sample programmes ---")
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM programmes ORDER BY start_time LIMIT 5")
        for row in cur.fetchall():
            print(dict(row))


def main():
    channels, programmes = parse_epg()
    channels_df, programmes_df = transform(channels, programmes)

    conn = get_connection()
    try:
        create_tables(conn)

        c_inserted, c_updated = upsert_channels(conn, channels_df)
        print(f"\nchannels:   {c_inserted} inserted, {c_updated} updated")

        p_inserted, p_updated = upsert_programmes(conn, programmes_df)
        print(f"programmes: {p_inserted} inserted, {p_updated} updated")

        verify(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()