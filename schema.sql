-- EPG schema: channels and scheduled programmes derived from an XMLTV feed.

CREATE TABLE IF NOT EXISTS channels (
    channel_id    TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS programmes (
    channel_id        TEXT NOT NULL REFERENCES channels(channel_id) ON DELETE CASCADE,
    start_time        TIMESTAMPTZ NOT NULL,
    stop_time         TIMESTAMPTZ NOT NULL,
    title             TEXT NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    category          TEXT NOT NULL DEFAULT 'Uncategorized',
    duration_minutes  INTEGER,
    ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (channel_id, start_time)
);

CREATE INDEX IF NOT EXISTS idx_programmes_start_time ON programmes (start_time);