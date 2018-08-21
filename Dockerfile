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

COPY test/WH897R_29453_000452.pdf $PDF/test/

RUN mkdir out
WORKDIR $PDF

EXPOSE 5555

CMD bash -c "sleep 10; $PDF/preprocess.sh training test/WH897R_29453_000452.pdf; python3 $PDF/server.py"
#CMD ["./preprocess.sh", "training", "test/WH897R_29453_000452.pdf"]

