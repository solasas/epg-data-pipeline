FROM apache/airflow:2.10.3-python3.9

COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.9.txt" \
    -r /requirements-airflow.txt