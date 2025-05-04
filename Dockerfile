FROM python:3.11-alpine

WORKDIR /App

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . /App

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]


