FROM python:3.10 AS builder
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y wget && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O /tmp/ffmpeg.tar.xz && \
    tar --strip-components 1 -C /usr/local/bin -xvf /tmp/ffmpeg.tar.xz $(tar -tf /tmp/ffmpeg.tar.xz  | grep "/ffmpeg$") && \
    rm -rf /tmp/ffmpeg.tar.xz && \
    apt-get purge -y --autoremove wget && \
    apt-get clean

FROM python:3.10-slim
ENV DEBIAN_FRONTEND="noninteractive"
COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY requirements.txt /usr/local/antipatibot/
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y libopus0 && \
    apt-get clean && \
    python3 -m pip install -r /usr/local/antipatibot/requirements.txt && \
    rm -rf /root/.cache /var/lib/apt/lists
COPY antipatibot.py /usr/local/antipatibot/
ENTRYPOINT ["/usr/local/antipatibot/antipatibot.py"]
