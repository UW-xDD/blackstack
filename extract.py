import sys
import os
from bs4 import BeautifulSoup
import psycopg2
import math
import re
import numpy as np
import itertools
import glob
np.set_printoptions(threshold=np.inf)

import heuristics
import helpers
import classifier
from config import Credentials

clf = classifier.create()

# Grab this much extra space around tables
padding = 20

'''
Tesseract hierarchy:

div.ocr_page
    div.ocr_carea
        p.ocr_par
            span.ocr_line
                span.ocrx_word
'''


def process_page(doc_stats, page):
    def find_above_and_below(extract):
        out = {
            'above': [],
            'below': [],
            'left': [],
            'right': []
        }
        for area_idx, area in enumerate(page['areas']):
            # Check if they overlap in x space
            if area['x1'] <= extract['x2'] and extract['x1'] <= area['x2']:
                # Check how *much* they overlap in x space
                # Number of pixels area overlaps with current extract extent
                overlap = max([ 0, abs(min([ area['x2'], extract['x2'] ]) - max([ extract['x1'], area['x1'] ])) ])
                area_length = area['x2'] - area['x1']
                percent_overlap = float(overlap) / area_length

                # If the area overlaps more than 90% in x space with the target area
                if percent_overlap >= 0.9:
                    # Check if this area is above or below the extract area
                    area_centroid = helpers.centroid(area)
                    extract_centroid = helpers.centroid(extract)
                    # If it is above
                    if area_centroid['y'] <= extract_centroid['y']:
                        # Work backwards so that when we iterate we start at the area closest to the extract
                        out['above'].insert(0, area_idx)
                    # If below
                    else:
                        out['below'].append(area_idx)

            # Check if they overlap in y space
            elif area['y1'] <= extract['y2'] and extract['y1'] <= area['y2']:
                overlap = max([ 0, abs(min([ area['y2'], extract['y2'] ]) - max([ extract['y1'], area['y1'] ])) ])
                area_length = area['y2'] - area['y1']
                percent_overlap = float(overlap) / area_length
                if percent_overlap >= 0.9:
                    area_centroid = helpers.centroid(area)
                    extract_centroid = helpers.centroid(extract)

                    if area_centroid['x'] <= extract_centroid['x']:
                        out['left'].insert(0, area_idx)
                    else:
                        out['right'].append(area_idx)
        return out


    def expand_extraction(extract_idx, props):
        # Iterate on above and below areas for each extract
        for direction, areas in extract_relations[extract_idx].iteritems():
            stopped = False
            for area_idx in extract_relations[extract_idx][direction]:
                # Iterate on all other extracts, making sure that extending the current one won't run into any of the others
                for extract_idx2, props2 in extract_relations.iteritems():
                    if extract_idx != extract_idx2:
                        will_intersect = helpers.rectangles_intersect(extracts[extract_idx2], helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))
                        if will_intersect:
                            stopped = True
                            continue

                if stopped:
                    continue

                if page['areas'][area_idx]['type'] == 'graphic' and direction == extracts[extract_idx]['direction']:
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif page['areas'][area_idx]['type'] == 'graphic caption':
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif page['areas'][area_idx]['type'] == 'graphic':
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif page['areas'][area_idx]['type'] == 'line':
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                elif ((page['areas'][area_idx]['type'] == 'body' or page['areas'][area_idx]['type'] == 'other') and page['areas'][area_idx]['word_height_avg'] < (doc_stats['word_height_avg'] - (doc_stats['word_height_avg_std']/4))):
                    extracts[extract_idx].update(helpers.enlarge_extract(extracts[extract_idx], page['areas'][area_idx]))

                else:
                    #print 'stop ', extracts[extract_idx]['name']
                    stopped = True


    # Find all areas that each area intersects
    areas = {}
    for idx_a, area_a in enumerate(page['areas']):
        areas[idx_a] = []

        for idx_b, area_b in enumerate(page['areas']):
            if idx_a != idx_b and helpers.rectangles_intersect(helpers.extractbbox(area_a['soup'].get('title')), helpers.extractbbox(area_b['soup'].get('title'))):
                areas[idx_a].append(idx_b)

#   If area intersects others, recursively get all intersections
    # new_areas = []
    # for area_idx in areas:
    #     if len(areas[area_idx]):
    #         new_area = { 'x1': 9999999, 'y1': 9999999, 'x2': -9999999, 'y2': -9999999 }
    #         new_area_consists_of = []
    #         all_intersections = [ areas[i] for i in areas if i in areas[area_idx]  ]
    #         # Flatten and filter
    #         all_intersections = set([ item for sublist in all_intersections for item in sublist ])
    #         for area in all_intersections:
    #             new_area_consists_of.append(area)
    #             new_area = helpers.enlarge_extract(new_area, helpers.extractbbox(page['areas'][area]['soup'].get('title')))
    #
    #         if new_area['x1'] != 9999999:
    #             new_area['consists_of'] = new_area_consists_of
    #             new_areas.append(new_area)
    #
    # # Filter unique new areas and remove areas that this new area covers
    # unique_new_areas = []
    # for area in new_areas:
    #     # Does this area overlap with any areas already accounted for?
    #     found = False
    #     for uidx, each in enumerate(unique_new_areas):
    #         # If it does, add it to that existing area
    #         if len(set(each['consists_of']).intersection(area['consists_of'])) > 0:
    #             found = True
    #             unique_new_areas[uidx]['consists_of'] = list(set(each['consists_of'] + area['consists_of']))
    #             new_area = helpers.enlarge_extract(each, area)
    #             for key in new_area:
    #                 unique_new_areas[uidx][key] = new_area[key]
    #
    #     if not found:
    #         unique_new_areas.append(area)
    #
    # print 'UNIQUE NEW AREAS', unique_new_areas

    # Find the captions/titles for charts, figures, maps, tables
    indicator_lines = []

    for line in page['lines']:
        # Remove nonsense
        clean_line = line.getText().strip().replace('\n', ' ').replace('  ', ' ').lower()
        # Find all lines that contain only a target word plus a number
        dedicated_line_matches = re.match('(table|figure|fig|map)(\.)? \d+(\.)?', clean_line, flags=re.IGNORECASE|re.MULTILINE)
        # Find all the lines that start with one of the target words and a number
        caption_matches = re.match('(table|figure|fig|map)(\.)? \d+(\.)', clean_line, flags=re.IGNORECASE|re.MULTILINE)
        # Problematic tesseract matches
        bad_tesseract_matches = re.match('^(table|figure|fig|map)(\.)? \w{1,5}(\S)?(\w{1,5})?(\.)?', clean_line, flags=re.IGNORECASE|re.MULTILINE)

        bbox = helpers.extractbbox(line.get('title'))
        # dedicated line (ex: Table 1)
        if dedicated_line_matches and dedicated_line_matches.group(0) == clean_line:
            bbox['name'] = dedicated_line_matches.group(0)
            print '  ', bbox['name'].replace('.', '')
            indicator_lines.append(bbox)

        # Other
        elif caption_matches:
            bbox['name'] = caption_matches.group(0)
            print '  ',  bbox['name'].replace('.', '')
            indicator_lines.append(bbox)

        elif bad_tesseract_matches:
            bbox['name'] = bad_tesseract_matches.group(0)
            print '  ', bbox['name'].replace('.', '')
            indicator_lines.append(bbox)

    # Assign a caption to each table, and keep track of which captions are assigned to tables. caption_idx: [area_idx, area_idx, ...]
    caption_areas = {}
    for area_idx, area in enumerate(page['areas']):
        if area['type'] == 'graphic':
            # Get the distances between the given area and all captions
            distances = [ { 'idx': line_idx, 'distance': helpers.min_distance(area, line) } for line_idx, line in enumerate(indicator_lines) ]

            # bail if there aren't any indicator_lines
            if len(distances) == 0:
                break

            distances_sorted = sorted(distances, key=lambda k: k['distance'])

            for line in distances_sorted:
                # Check if it intersects any text areas
                potential_area = helpers.enlarge_extract(area, indicator_lines[line['idx']])

            distances = [helpers.min_distance(area, line) for line in indicator_lines]

            # The index of the nearest caption
            if len(distances) == 0:
                break

            nearest_caption = distances.index(min(distances))

            # TODO: Need to check if expanding to this caption would intersect any text areas that don't intersect the caption
            # Assign the nearest caption to the area
            area['graphic caption'] = nearest_caption
            # Bookkeep
            try:
                caption_areas[nearest_caption].append(area_idx)
            except:
                caption_areas[nearest_caption] = [area_idx]

    '''
    If a page has tables unassigned to captions, those go in a different pile

    When it comes time to create extract areas from them, they play by different rules:
        + The starting extract area is simply the area(s) determined to be tables
        + Extract areas can eat each other / be combined
    '''

        # Need to go find the tables and create appropriate areas
        # Basically, treat them as extracts that can overlap, and then merge intersecting extracts

        # alternative_captions = []
        #
        # for line in page['lines']:
        #     # First make sure this line doesn't exist any tables
        #     line_bbox = helpers.extractbbox(line.get('title'))
        #     table_intersections = []
        #     for table in all_tables:
        #         if helpers.rectangles_intersect(page['areas'][table], line_bbox):
        #             table_intersections.append(True)
        #         else:
        #             table_intersections.append(False)
        #
        #     # If it does, skip it
        #     if True in table_intersections:
        #         continue
        #
        #     # Remove nonsense
        #     clean_line = line.getText().strip().replace('\n', ' ').replace('  ', ' ').lower()
        #     # mediocre caption matches
        #     ok_matches = re.match('^(.*?) \d+(\.)?', clean_line, flags=re.IGNORECASE)
        #
        #     '''
        #     Caption is good enough if the following are satisfied:
        #         + the average word height is less than the document's average word height - 1/4 average word height std
        #         + The line it is on does not intersect and table
        #     '''
        #     if ok_matches and line_word_height(line) < (doc_stats['word_height_avg'] - (doc_stats['word_height_avg_std']/4)):
        #          line_bbox['name'] = ok_matches.group(0)
        #          print 'Alt caption - ', line_bbox['name']
        #          alternative_captions.append(line_bbox)



    # Sanity check the caption-area assignments
    for caption, areas in caption_areas.iteritems():
        # Only check if the caption is assigned to more than one area
        if len(areas) > 1:
            # draw a line through the middle of the caption that spans the page
            '''
              x1,y1 0 --------------
                    |               |
            - - - - | - - - - - - - | - - - - <-- Create this line
                    |               |
                     -------------- 0 x2,y2
            '''
            caption_line_y = indicator_lines[caption]['y1'] + (indicator_lines[caption]['y2'] - indicator_lines[caption]['y1'])
            caption_line = {
                'x1': page['page']['x1'],
                'y1': caption_line_y,
                'x2': page['page']['x2'],
                'y2': caption_line_y
            }

            # Get a list of unique combinations of areas for this caption (example: [(0,1), (1,3)] )
            area_combinations = list(itertools.combinations(caption_areas[caption], 2))

            # Draw a line between them
            '''
             -----------
            |           |
            |     a     |
            |      \    |
             -------\---
                     \ <------ area_connection_line
                 -----\-
                |      \|
        - - - - | - - -|\ - - - - - - -
                |      | \
                 ------   \
                           \
                    --------\--------------
                   |         \             |
                   |          \            |
                   |           b           |
                   |                       |
                   |                       |
                    -----------------------
            '''

            for pair in area_combinations:
                a = helpers.centroid(page['areas'][pair[0]])
                b = helpers.centroid(page['areas'][pair[1]])
                area_line = {
                    'x1': a['x'],
                    'y1': a['y'],
                    'x2': b['x'],
                    'y2': b['y']
                }
                # Check if the line intersects the caption line. If it does, determine which of the 'tables' is more table-y
                if helpers.lines_intersect(caption_line, area_line):
                    if page['areas'][pair[0]]['classification_p'] > page['areas'][pair[1]]['classification_p']:
                        caption_areas[caption] = [ area for area in caption_areas[caption] if area != pair[1]]
                    else:
                        page['areas'][pair[0]]['type'] = 'graphic'
                        caption_areas[caption] = [ area for area in caption_areas[caption] if area != pair[0]]

    # Extracts are bounding boxes that will be used to actually extract the tables
    extracts = []
    for caption, areas in caption_areas.iteritems():
        print indicator_lines[caption]
        area_of_interest_centroid_y_mean = np.mean([ helpers.centroid(page['areas'][area])['y'] for area in areas ])
        indicator_line_centroid_y = helpers.centroid(indicator_lines[caption])['y']

        areas_of_interest = [ page['areas'][area] for area in areas ]

        # Find the area that the indicator line intersects
        for area in page['areas']:
            if helpers.rectangles_intersect(area, indicator_lines[caption]):
                areas_of_interest.append(area)
        #areas_of_interest.append(indicator_lines[caption])

        # The extract is designated by the min/max coordinates of the caption and cooresponding table(s)
        extracts.append({
            'name': indicator_lines[caption]['name'],
            'direction': 'below' if  area_of_interest_centroid_y_mean > indicator_line_centroid_y else 'above',
            'indicator_line': indicator_lines[caption],
            'x1': min([a['x1'] for a in areas_of_interest]) - padding,
            'y1': min([a['y1'] for a in areas_of_interest]) - padding,
            'x2': max([a['x2'] for a in areas_of_interest]) + padding,
            'y2': max([a['y2'] for a in areas_of_interest]) + padding
        })

    # Make sure each table was assigned a caption
    assigned_tables = []
    unassigned_tables = []
    for caption_idx, areas in caption_areas.iteritems():
        assigned_tables = assigned_tables + areas

    all_tables = []
    for area_idx, area in enumerate(page['areas']):
        if area['type'] == 'graphic':
            all_tables.append(area_idx)

    if sorted(assigned_tables) == sorted(all_tables):
        print 'all tables have a caption on page', page['page_no']
    else:
        unassigned_tables = set(all_tables).difference(assigned_tables)
        print 'Not all tables have a caption on page', page['page_no']
        print 'Not assigned - ', unassigned_tables

    orphan_extracts = []
    for table in unassigned_tables:

        # TODO: parameterize arbitrary cut off
        if page['areas'][table]['classification_p'] > 0.5:
            orphan_extracts.append(helpers.expand_area(page['areas'][table], page['areas']))

    orphan_extracts = helpers.union_extracts(orphan_extracts)

    for extract in orphan_extracts:
        extract['name'] = 'Unknown'
        extract['direction'] = 'None'
    #    extracts.append(extract)


    # Find all areas that overlap in x space and are above and below the extracts
    extract_relations = {}
    for extract_idx, extract in enumerate(extracts):
        extract_relations[extract_idx] = find_above_and_below(extract)

    for extract_idx, extract in enumerate(extracts):
        expand_extraction(extract_idx, find_above_and_below(extract))

    # for extract_idx, props in extract_relations.iteritems():
    #     expand_extraction(extract_idx, props)

    for extract in orphan_extracts:
        # Find out if a good extraction already covers this area
        extract_poly = helpers.make_polygon(extract)
        covers = False
        for each in extracts:
            intersection = extract_poly.intersection(helpers.make_polygon(each))
            if intersection >= (extract_poly.area * 0.9):
                covers = True

        if not covers:
            extracts.append(extract)
            extract_relations[len(extracts) - 1] = find_above_and_below(extract)
            expand_extraction(len(extracts) - 1, extract_relations[len(extracts) - 1])

    return extracts


# Entry into table extraction
def extract_tables(document_path):
    # Connect to Postgres
    connection = psycopg2.connect(
        dbname=Credentials.PG_DATABASE,
        user=Credentials.PG_USERNAME,
        password=Credentials.PG_PASSWORD,
        host=Credentials.PG_HOST,
        port=Credentials.PG_PORT
    )
    cursor = connection.cursor()

    page_paths = glob.glob(document_path + '/tesseract/*.html')

    pages = []
    text_layer = ''

    # Read in each tesseract page with BeautifulSoup so we can look at the document holistically
    for page_no, page in enumerate(page_paths):
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
            # Record the OCR-identified text
            text_layer += soup.getText()

    # map/reduce
    page_areas = [ page['areas'] for page in pages ]

    # Calculate summary stats for the document from all areas identified by Tesseract
    doc_stats = helpers.summarize_document([ area for areas in page_areas for area in areas ])

    # Classify areas
    for idx, page in enumerate(pages):
        for area in page['areas']:
            area['classification'] = heuristics.classify(area, doc_stats, page['areas'])
            area['classification']['page_no'] = page['page_no']
            # Use the model to assign an area type and probabilty of that area type
            probabilities = clf.predict_proba([ heuristics.classify_list(area, doc_stats, page['areas']) ])
            # Apply a label to each probability
            classifications = zip(clf.classes_, probabilities)
            # Sort by highest probability
            classifications.sort(key=lambda x: x[1], reverse=True)

            area['classification_p'] = classifications[0][0]

            area['type'] = clf.predict([ heuristics.classify_list(area, doc_stats, page['areas']) ])


    # Attempt to identify all charts/tables/etc in the paper by looking at the text layer
    # i.e. It is useful for us to know if the text mentions "see table 4", because if the caption
    # for table 4 is distorted in the text layer ("teble 4", for example), we can still guess that
    # it is table 4 because of it's position in the document and our prior knowledge that a table 4
    # exists
    text_layer = text_layer.strip().replace('\n', ' ').replace('  ', ' ').lower()
    figures = []
    for result in re.findall('(table|figure|fig|map|appendix|app|appx|tbl)(\.)? (\d+)(\.)?', text_layer, flags=re.IGNORECASE):
        figures.append(' '.join(' '.join(result).replace('.', '').replace('figure', 'fig').split()).lower())

    # Clean up the list of figures/tables/etc
    figures = sorted(set(figures))
    figure_idx = {}
    for fig in figures:
        parts = fig.split(' ')
        # Need to try/except because often times the "number" is actually a string that cannot be parsed into an integer
        if parts[0] in figure_idx:
            try:
                figure_idx[parts[0]].append(int(parts[1]))
            except:
                continue
        else:
            try:
                figure_idx[parts[0]] = [ int(parts[1]) ]
            except:
                continue

    # Clean up for reformat
    for key in figure_idx:
        figure_idx[key] = helpers.clean_range(sorted(set(figure_idx[key])))

    # map/reduce
    area_stats = [ area for areas in page_areas for area in areas ]


    # Most documents only contain one page height, but others mix landscape and portrait pages
    # Figure out which is the most common
    doc_stats['page_height'] = np.bincount([ page['page']['y2'] - page['page']['y1'] for page in pages ]).argmax()
    doc_stats['page_width'] = np.bincount([ page['page']['x2'] - page['page']['x1'] for page in pages ]).argmax()

    # Find out if a header or footer is present in the document - make sure we don't include them in extracts
    doc_stats['header'], doc_stats['footer'] = helpers.get_header_footer(pages, doc_stats['page_height'], doc_stats['page_width'])


    doc_stats['found_tables'] = figure_idx
    print 'these tables were found --'

    for ttype in figure_idx:
        print '    ', ttype, figure_idx[ttype]

    for page in pages:
        page_extracts = process_page(doc_stats, page)

        found = []
        for e in page_extracts:
            if e['name'] in found:
                 e['name'] = e['name'] + '*'

            found.append(e['name'])


        for table in page_extracts:
            helpers.extract_table(document_path, page['page_no'], table)



# WAT WHY IS THIS HERE
import argparse

parser = argparse.ArgumentParser(
    description="Extract tables from a pre-processed PDF",
    epilog="Example usage: python extract.py ~/documents/my_pdf")

parser.add_argument(nargs="?", dest="doc_path",
    default="", type=str,
    help="The path to the desired document. The folder should contain the folders 'png' and 'tesseract'")

arguments = parser.parse_args()

if len(arguments.doc_path) == 0:
    print "Please enter a valid document path"
    sys.exit(1)


extract_tables(arguments.doc_path)
