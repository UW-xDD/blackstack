import sys
import glob
import heuristics
import helpers
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extensions import AsIs

from config import Credentials
# Connect to Postgres
connection = psycopg2.connect(
    dbname=Credentials.PG_DATABASE,
    user=Credentials.PG_USERNAME,
    password=Credentials.PG_PASSWORD,
    host=Credentials.PG_HOST,
    port=Credentials.PG_PORT
)
cursor = connection.cursor()

if len(sys.argv) != 2:
    print 'No document provided'
    sys.exit(1)

doc_id = sys.argv[1]

page_paths = glob.glob('./docs/' + doc_id + '/tesseract/*.html')

pages = []
for page_no, page in enumerate(page_paths):
    # Read in each tesseract page with BeautifulSoup so we can look at the document holistically
    with open(page) as hocr:
        text = hocr.read()
        soup = BeautifulSoup(text, 'html.parser')
        merged_areas = helpers.merge_areas(soup.find_all('div', 'ocr_carea'))
        pages.append({
            'page_no': page.split('/')[-1].replace('.html', '').replace('page_', ''),
            'soup': soup,
            'page': helpers.extractbbox(soup.find_all('div', 'ocr_page')[0].get('title')),
            'areas': [ helpers.area_summary(area) for area in merged_areas ],
            'lines': [ line for line in soup.find_all('span', 'ocr_line') ]
        })

# map/reduce
page_areas = [ page['areas'] for page in pages ]

# Calculate summary stats for the document from all areas identified by Tesseract
doc_stats = helpers.summarize_document([ area for areas in page_areas for area in areas ])

# Classify areas
for idx, page in enumerate(pages):
    for area in page['areas']:
        classification = heuristics.classify(area, doc_stats, page['areas'])
        classification['page_no'] = page['page_no']

        cursor.execute("""
            INSERT INTO areas (page_no, has_words, line_intersect, small_text, small_leading, is_line, is_top_or_bottom, mostly_blank, very_separated_words, little_word_coverage, normal_word_separation,normal_word_coverage, best_caption, good_caption, ok_caption, overlap, proportion_alpha, offset_words, n_gaps, n_lines, x1, y1, x2, y2, area)
            VALUES (%(page_no)s, %(has_words)s, %(line_intersect)s, %(small_text)s, %(small_leading)s, %(is_line)s, %(is_top_or_bottom)s, %(mostly_blank)s, %(very_separated_words)s, %(little_word_coverage)s, %(normal_word_separation)s, %(normal_word_coverage)s, %(best_caption)s, %(good_caption)s, %(ok_caption)s, %(overlap)s, %(proportion_alpha)s, %(offset_words)s, %(n_gaps)s, %(n_lines)s, %(x1)s, %(y1)s, %(x2)s, %(y2)s, %(area)s)
            RETURNING area_id
        """, classification)
        area_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO area_docs (area_id, doc_id)
            VALUES (%(area_id)s, %(doc_id)s)
        """, {
            "area_id": area_id,
            "doc_id": doc_id
        })
        connection.commit()
