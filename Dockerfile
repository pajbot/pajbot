FROM python:alpine AS build
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev zlib-dev jpeg-dev postgresql-dev
COPY ./requirements.txt /app
RUN python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
RUN find /app/venv -name '__pycache__' | xargs rm -rf

FROM python:alpine
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apk add --no-cache git libpq libffi libjpeg-turbo
COPY . /app
COPY --from=build /app/venv /app/venv
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
RUN pip --no-cache-dir install supervisor
RUN find /usr/local/lib/python3.8 -name '__pycache__' | xargs rm -r
RUN chmod -R 777 /app/static
CMD ["/usr/local/bin/supervisord"]