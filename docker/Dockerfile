FROM debian:10

RUN apt-get update
RUN apt-get install -y git libssl-dev libpq-dev python3 python3-pip python3-venv

WORKDIR "/opt/pajbot"
COPY "./" "./"

RUN ./scripts/venvinstall.sh
