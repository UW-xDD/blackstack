#! /bin/bash

if [ $# -lt 1 ]
  then echo -e "Please provide a document type and input PDF. Available types are training and classified. Example: ./preprocess.sh training ~/Downloads/document.pdf"
  exit 1
fi

if [ "$1" != "training" ] && [ "$1" != "classified" ]
  then echo -e "You must provide a valid processing type. Please use training for processing data for annotation or classified for a document you'd like to run the model on."
  exit 1
fi

filename=$(basename "$2")
docname="${filename%.*}"

mkdir -p docs/$1/$docname
mkdir -p docs/$1/$docname/png
mkdir -p docs/$1/$docname/tesseract
if [ "$1" == "classified" ]
  then mkdir -p docs/$1/$docname/extracts
fi

gs -dBATCH -dNOPAUSE -sDEVICE=png16m -dGraphicsAlphaBits=4 -dTextAlphaBits=4 -r600 -sOutputFile="./docs/$1/$docname/png/page_%d.png" $2

cp $2 ./docs/$docname/orig.pdf

ls ./docs/$docname/png | grep -o '[0-9]\+' | parallel -j 4 "./process.sh $1 $docname {}"

if [ "$1" == "training" ]
  then python summarize.py $docname
fi

echo "$filename has been processed and can be found in ./docs/$1/$docname"
