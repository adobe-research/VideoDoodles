
FROM nikolaik/python-nodejs

WORKDIR /app

COPY ["package.json", "package-lock.json*", "./"]

RUN npm install

COPY . .

RUN npm run build

RUN pip install -U tiny-http-server

WORKDIR public
CMD ["tiny-http-server", "--bind", "0.0.0.0",  "--port", "8000"]
# CMD ["sleep","3600"]