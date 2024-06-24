import os

from datetime import datetime
from airflow.decorators import dag, task
import pendulum

from youtube_workflows import (
    restore_token,
    pandas_load,
    update_manifest,
    download_new,
    backup_metadata,
    upload_backup,
    restore_uploaded,
)
import logging


@dag(
    schedule="0 */12 * * *",
    start_date=pendulum.datetime(2024, 4, 4, tz="UTC"),
    catchup=False,
    tags=["youtube", "backup"],
)
def restore_token_dag():
    @task()
    def restore_token_task():
        restore_token()

    restore_token_task()


restore_token_dag()


@dag(
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2024, 4, 4, tz="UTC"),
    catchup=False,
    tags=["youtube", "backup"],
)
def backup_dag():
    @task()
    def pandas_load_task():
        return pandas_load()

    @task()
    def update_manifest_task(resp):
        update_manifest(resp)

    @task()
    def download_new_task():
        download_new()

    resp = pandas_load_task()
    update_manifest_task(resp) >> download_new_task()


backup_dag()


@dag(
    schedule="0 6 * * 1",
    start_date=pendulum.datetime(2024, 4, 4, tz="UTC"),
    catchup=False,
    tags=["youtube", "backup"],
)
def backup_metadata_dag():
    @task()
    def backup_metadata_task():
        backup_metadata()

    backup_metadata_task()


backup_metadata_dag()


@dag(
    schedule="0 10 * * *",
    start_date=pendulum.datetime(2024, 4, 4, tz="UTC"),
    catchup=False,
    tags=["youtube", "backup"],
)
def upload_backup_dag():
    @task()
    def pandas_load_task():
        return pandas_load()

    @task()
    def upload_backup_task(resp):
        upload_backup(resp)

    @task()
    def restore_uploaded_task(resp):
        restore_uploaded(resp)

    resp = pandas_load_task()
    upload_backup_task(resp)
    restore_uploaded_task(resp)


upload_backup_dag()
