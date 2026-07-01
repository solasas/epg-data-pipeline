"""FastAPI application exposing the EPG data stored in PostgreSQL."""
from datetime import date as date_type, datetime, time, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from db.connection import get_connection

app = FastAPI(title="EPG API", description="Electronic Program Guide data API")


def _fetch_all(query, params=()):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


@app.get("/channels")
def get_channels():
    channels = _fetch_all("SELECT channel_id, display_name FROM channels ORDER BY channel_id")
    if not channels:
        raise HTTPException(status_code=404, detail="No channels found.")
    return channels


@app.get("/schedule")
def get_schedule(
    channel_id: Optional[str] = Query(None, description="Filter by channel id, e.g. 5.uk"),
    date: Optional[date_type] = Query(None, description="Filter by calendar date (UTC), e.g. 2026-07-06"),
    category: Optional[str] = Query(None, description="Filter by category, e.g. Sports"),
):
    conditions = []
    params = []

    if channel_id:
        conditions.append("channel_id = %s")
        params.append(channel_id)

    if date:
        # Compare against explicit UTC day boundaries rather than casting
        # start_time::date, which would depend on the DB session's timezone.
        start_of_day = datetime.combine(date, time.min, tzinfo=timezone.utc)
        end_of_day = start_of_day + timedelta(days=1)
        conditions.append("start_time >= %s AND start_time < %s")
        params.extend([start_of_day, end_of_day])

    if category:
        conditions.append("category ILIKE %s")
        params.append(category)

    query = "SELECT * FROM programmes"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY start_time"

    programmes = _fetch_all(query, params)
    if not programmes:
        raise HTTPException(status_code=404, detail="No programmes found matching the given filters.")
    return programmes


@app.get("/schedule/now")
def get_now_airing():
    now = datetime.now(timezone.utc)
    programmes = _fetch_all(
        "SELECT * FROM programmes WHERE start_time <= %s AND stop_time >= %s ORDER BY channel_id",
        (now, now),
    )
    if not programmes:
        raise HTTPException(status_code=404, detail="Nothing is currently airing.")
    return programmes
