# ocr-classify

A machine learning approach to table and figure extraction

## Installation

First install dependencies
````
brew install ghostscript parallel tesseract
````

Assuming you have Postgres already installed, set up the database:
````
createdb ocr-classify
psql ocr-classify < schema.sql
````

## Info
summarize.py - calculates doc stats for an article and inserts them into pg

heuristics.py - the factors caculated for each area

# Funding
Development supported by NSF ICER 1343760

# License
MIT
