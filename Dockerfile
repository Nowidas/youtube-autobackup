FROM apache/airflow
COPY ./requirements.txt ./requirements.txt
# COPY ./token.json ./token.json
RUN pip install -r ./requirements.txt