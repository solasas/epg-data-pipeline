"""Daily EPG ingestion pipeline: extract raw XMLTV -> clean with pandas -> load into Postgres."""
import os
import sys
from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

PROJECT_DIR = "/opt/airflow/project"
TMP_DIR = os.path.join(PROJECT_DIR, "tmp")

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Loaded explicitly (not via cwd-based discovery) since this module-level code
# runs at DAG parse time, before any task has chdir'd into PROJECT_DIR.
load_dotenv(dotenv_path=os.path.join(PROJECT_DIR, ".env"))


def notify_slack_on_failure(context):
    """on_failure_callback: post a Slack alert when a task exhausts its retries."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set — skipping Slack alert. See task logs for the failure.")
        return

    task_instance = context["task_instance"]
    message = (
        ":rotating_light: *Airflow task failed*\n"
        f"*DAG*: `{context['dag'].dag_id}`\n"
        f"*Task*: `{task_instance.task_id}`\n"
        f"*Run*: `{context['run_id']}`\n"
        f"*Error*: `{context.get('exception')}`\n"
        f"<{task_instance.log_url}|View logs>"
    )

    try:
        response = requests.post(webhook_url, json={"text": message}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        # Don't let a failed alert mask the original task failure.
        print(f"Failed to send Slack alert: {e}")


def run_extract():
    os.chdir(PROJECT_DIR)
    import extract
    extract.main()


def run_transform():
    os.chdir(PROJECT_DIR)
    from parse import parse_epg
    from transform import transform

    channels, programmes = parse_epg()
    channels_df, programmes_df = transform(channels, programmes)

    # Each task runs in its own process, so DataFrames can't be handed to the
    # next task in memory. We persist them here, the same way extract.py
    # hands raw XML to parse.py via raw_epg.xml on disk.
    os.makedirs(TMP_DIR, exist_ok=True)
    channels_df.to_pickle(os.path.join(TMP_DIR, "channels.pkl"))
    programmes_df.to_pickle(os.path.join(TMP_DIR, "programmes.pkl"))


def run_load():
    os.chdir(PROJECT_DIR)
    import pandas as pd

    from db.connection import get_connection
    from load import create_tables, upsert_channels, upsert_programmes, verify

    channels_df = pd.read_pickle(os.path.join(TMP_DIR, "channels.pkl"))
    programmes_df = pd.read_pickle(os.path.join(TMP_DIR, "programmes.pkl"))

    conn = get_connection()
    try:
        create_tables(conn)
        c_inserted, c_updated = upsert_channels(conn, channels_df)
        print(f"channels:   {c_inserted} inserted, {c_updated} updated")
        p_inserted, p_updated = upsert_programmes(conn, programmes_df)
        print(f"programmes: {p_inserted} inserted, {p_updated} updated")
        verify(conn)
    finally:
        conn.close()


default_args = {
    "owner": "epg-pipeline",
    "retries": 1,
    "on_failure_callback": notify_slack_on_failure,
}

with DAG(
    dag_id="epg_pipeline",
    description="Download, clean, and load the daily XMLTV EPG feed into Postgres",
    default_args=default_args,
    schedule="0 0 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["epg"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract",
        python_callable=run_extract,
    )

    transform_task = PythonOperator(
        task_id="transform",
        python_callable=run_transform,
    )

    load_task = PythonOperator(
        task_id="load",
        python_callable=run_load,
    )

    extract_task >> transform_task >> load_task