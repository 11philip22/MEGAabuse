FROM python:slim-buster

RUN mkdir /app
COPY * /app/
WORKDIR /app
RUN pip install -r requirements.txt

USER 1000
ENTRYPOINT ["python", "MEGAabuse.py"]