FROM debian:stable-20210408

RUN apt-get update && apt-get -y install \
        python3-pip \
        && rm -rf /var/lib/apt/lists

RUN pip3 install \
        bokeh==2.3.1 \
        pandas==1.2.4
