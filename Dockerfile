FROM python:3.13-slim

RUN apt update && apt install -y locales locales-all

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

COPY ./gunicorn.py /gunicorn.py

#CMD ["python3", "app.py"]
CMD ["gunicorn", "-c", "/gunicorn.py", "app:app"]
