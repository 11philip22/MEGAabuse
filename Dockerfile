FROM archlinux/base

RUN pacman -Sy --noconfirm \
           python \
           libffi
RUN pacman -Scc --noconfirm

RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
    python get-pip.py && rm get-pip.py

RUN mkdir /app
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt --no-cache-dir

RUN chown -R 1000:1000 /app

USER 1000:1000
#ENTRYPOINT ["python", "MEGAabuse.py"]



#FROM python:slim-buster
#
#RUN mkdir /app
#ADD . /app
#WORKDIR /app
#RUN pip install -r requirements.txt --no-cache-dir
#
#RUN chown -R 1000:1000 /app
#
#RUN apt-get update && apt-get install -y --no-install-recommends \
#    libpcrecpp0v5 \
#    libpcre3 libpcre3-dev \
#    libc6 \
#    libcurl4 \
#    libglib2.0-0 \
#    libssl1.1
#RUN rm -rf /var/lib/apt/lists/*
#RUN ln -s /lib/x86_64-linux-gnu/libpcre.so.3 /lib/x86_64-linux-gnu/libpcre.so.1
#
#USER 1000:1000
##ENTRYPOINT ["python", "MEGAabuse.py"]
#CMD bash