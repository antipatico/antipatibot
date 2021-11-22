FROM debian:11.1
ENV DEBIAN_FRONTEND="noninteractive"
COPY antipatibot.py requirements.txt /usr/local/antipatibot/
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3 python3-pip python3-dev libffi-dev libnacl-dev ffmpeg && \
    apt-get clean && \
    python3 -m pip install -r /usr/local/antipatibot/requirements.txt && \
    rm -rf /root/.cache /var/lib/apt/lists
VOLUME /antipatibot
