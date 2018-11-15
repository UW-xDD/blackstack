#!/bin/sh


if [ -z "${BLACKSTACK_MODE}" ]
then
    echo "Please specify BLACKSTACK_MODE as an envvar"
    exit 1
else
    BLACKSTACK_MODE=${BLACKSTACK_MODE}
    echo Running blackstack in $BLACKSTACK_MODE mode.
    if [ "$BLACKSTACK_MODE" = "classified" ] 
    then
        echo classified
        ./preprocess.sh classified test/1-s2.0-0031018280900164-main.pdf ; 
        python3 extract.py ./docs/classified/1-s2*/
    elif [ "$BLACKSTACK_MODE" = "training" ] 
    then
        echo training
        ./preprocess.sh training test/1-s2.0-0031018280900164-main.pdf
        python3 server.py
    else
        echo "Unknown blackstack mode specified. Please choose classified or training."
    fi
fi
