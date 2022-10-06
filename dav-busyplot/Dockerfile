FROM debian:stable-20221004

RUN apt-get update && apt-get -y install \
        python3-pip \
        && rm -rf /var/lib/apt/lists

RUN pip3 install \
        bokeh==2.4.3 \
        pandas==1.5.0
