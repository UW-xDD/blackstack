#! /bin/bash

if [ $# -lt 1 ]
  then echo -e "Please provide an input PDF. Example: ./prep.sh ~/Downloads/document.pdf"
  exit 1
fi

filename=$(basename "$1")
docname="${filename%.*}"

mkdir -p docs/$docname
mkdir -p docs/$docname/png
mkdir -p docs/$docname/tesseract
mkdir -p docs/$docname/tables

gs -dBATCH -dNOPAUSE -sDEVICE=png16m -dGraphicsAlphaBits=4 -dTextAlphaBits=4 -r600 -sOutputFile="./docs/$docname/png/page_%d.png" $1

cp $1 ./docs/$docname/orig.pdf

ls ./docs/$docname/png | grep -o '[0-9]\+' | parallel -j 4 "./process.sh $docname {}"

echo 'Done'
