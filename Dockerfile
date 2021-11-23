FROM debian:11.1
ENV DEBIAN_FRONTEND="noninteractive"
COPY antipatibot.py requirements.txt /usr/local/antipatibot/
VOLUME /antipatibot
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3 python3-pip python3-dev libffi-dev libnacl-dev libopus0 wget && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O /tmp/ffmpeg.tar.xz && \
    tar --strip-components 1 -C /usr/local/bin -xvf /tmp/ffmpeg.tar.xz $(tar -tf /tmp/ffmpeg.tar.xz  | grep "/ffmpeg$") && \
    rm -rf /tmp/ffmpeg.tar.xz && \
    apt-get purge -y --autoremove wget && \
    apt-get clean && \
    python3 -m pip install -r /usr/local/antipatibot/requirements.txt && \
    rm -rf /root/.cache /var/lib/apt/lists
