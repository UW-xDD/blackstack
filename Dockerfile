FROM tesseractshadow/tesseract4re

RUN apt update -y

# TODO when bandwidth upgrade

RUN apt install git -y
RUN apt install poppler-utils ghostscript -y
RUN apt install parallel -y
RUN apt install python3 python3-pip python-tk -y
# tk stuff wants these options for headless pyplot
COPY matplotlibrc /root/.config/matplotlib/matplotlibrc

COPY requirements.txt .
RUN pip3 install -r requirements.txt

ENV PDF=/app/pdf
ENV PYTHONPATH=$PDF
WORKDIR $PDF

COPY *sh $PDF/
COPY *py $PDF/
COPY annotator $PDF/
COPY config.py.env $PDF/config.py

COPY 1-s2.0-0031018280900164-main.pdf $PDF/test/
ARG BLACKSTACK_MODE

RUN mkdir out
WORKDIR $PDF

EXPOSE 5555

CMD ["./blackstack_wrapper.sh"]
