"""Table schema for the EPG data model (XMLTV channels + programmes)."""
from db.connection import get_connection

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    channel_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS programmes (
    id SERIAL PRIMARY KEY,
    channel_id TEXT NOT NULL REFERENCES channels(channel_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    stop_time TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_programmes_channel_start
    ON programmes (channel_id, start_time);
"""


def create_tables():
    """Create the channels/programmes tables if they don't exist yet."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
    print("Tables ready: channels, programmes")