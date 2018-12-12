#!/bin/sh


if [ -z "${BLACKSTACK_MODE}" ]
then
    echo "No BLACKSTACK_MODE specified -- assuming classification mode on prebuilt model."
    BLACKSTACK_MODE='classified'
else
    BLACKSTACK_MODE=${BLACKSTACK_MODE}
fi

echo Running blackstack in $BLACKSTACK_MODE mode.
if [ "$BLACKSTACK_MODE" = "classified" ] 
then
    for doc in input/*.pdf;
    do
        filename=$(basename "$doc")
        docname="${filename%.*}"
        echo ./preprocess.sh classified input/$filename
        ./preprocess.sh classified input/$filename
        echo python3 extract.py ./docs/classified/$docname/
        python3 extract.py ./docs/classified/$docname/
    done
elif [ "$BLACKSTACK_MODE" = "training" ] 
then
    for doc in input/*.pdf;
    do
        filename=$(basename "$doc")
        docname="${filename%.*}"
        ./preprocess.sh training input/$filename
    done
    python3 server.py
else
    echo "Unknown blackstack mode specified. Please choose classified or training."
    exit 1
fi
