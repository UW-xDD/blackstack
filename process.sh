#! /bin/bash

tesseract ./docs/$1/png/page_$2.png ./docs/$1/tesseract/page_$2.html hocr
mv ./docs/$1/tesseract/page_$2.html.hocr ./docs/$1/tesseract/page_$2.html
