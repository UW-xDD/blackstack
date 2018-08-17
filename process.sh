#! /bin/bash

tesseract ./docs/$1/$2/png/page_$3.png ./docs/$1/$2/tesseract/page_$3.html hocr
mv ./docs/$1/$2/tesseract/page_$3.html.hocr ./docs/$1/$2/tesseract/page_$3.html
