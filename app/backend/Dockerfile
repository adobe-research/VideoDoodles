
FROM python:3.11

WORKDIR /app

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-u", "app.py"]