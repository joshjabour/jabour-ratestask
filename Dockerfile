FROM postgres:12 as db
COPY rates.sql /docker-entrypoint-initdb.d/
EXPOSE 5432
ENV POSTGRES_PASSWORD=ratestask

FROM python:3.9-slim-buster as app
WORKDIR /python-docker
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
ENV POSTGRES_DB_HOST=ratesdb
ENV POSTGRES_DB_NAME=postgres
ENV POSTGRES_USERNAME=postgres
ENV POSTGRES_PASSWORD=ratestask