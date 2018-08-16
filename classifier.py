from psycopg2.extensions import AsIs
import psycopg2.extras
import numpy as np
from sklearn import svm
import helpers
import heuristics

# Connect to Postgres
connection = psycopg2.connect(dbname='blackstack', user='john', host='localhost', port='5432')
#cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cursor = connection.cursor()

def create():
    cursor.execute("""
        SELECT
            a.area_id,
            area_docs.doc_id,
            page_no,
            labels.name AS label,
            has_words::int,
            line_intersect::int,
            small_text::int,
            small_leading::int,
            is_line::int,
            is_top_or_bottom::int,
            mostly_blank::int,
            very_separated_words::int,
            little_word_coverage::int,
            normal_word_separation::int,
            normal_word_coverage::int,
            best_caption::int,
            good_caption::int,
            ok_caption::int,
            overlap::int,
            offset_words::int,
            proportion_alpha::float,
            area::float / (select max(area) from areas) as area,
            n_gaps::float / (select max(n_gaps) from areas) as n_gaps,
            n_lines::float / (select max(n_lines) from areas) as n_lines
        FROM areas a
        JOIN area_docs ON a.area_id = area_docs.area_id
        JOIN area_labels al ON al.area_id = a.area_id
        JOIN labels ON labels.label_id = al.label_id
    """)
    data = cursor.fetchall()

    # Omit area_id, doc_id, page_no, and label_name
    train = [ list(d[4:]) for d in data ]

    label = np.array([ d[3] for d in data ])
    #index = [ d[0:3] for d in data ]

    # gamma - influence of a single training example. low = far, high = close
    # C - low = less freedom, high = more freedom
    #clf = svm.SVC(gamma=0.001, C=100., probability=True, cache_size=500)
    clf = svm.SVC(gamma=1, C=100, probability=True, cache_size=500, kernel='rbf')

    clf.fit(train, label)

    return clf

def classify(pages, doc_stats):
    clf = create()

    for idx, page in enumerate(pages):
        for area in page['areas']:
            classification = heuristics.classify_list(area, doc_stats, page['areas'])

            estimated_label = clf.predict([classification])[0]
            p = zip(clf.classes_, clf.predict_proba([classification])[0])

            best_p = max([ d[1] for d in p if d[0] != 'other' ])
            if best_p < 0.6:
                estimated_label = 'unknown'

            area['label'] = estimated_label


        # Go through again, validating body areas
        # if a caption can't be expanded without running into body, it's not a caption
        for area in page['areas']:
            if area['label'] == 'graphic caption':
                valid = False
                for each in [ d for d in page['areas'] if d['label'] == 'graphic']:
                    if valid:
                        break
                    expanded = helpers.enlarge_extract(area, each)
                    for body in [ q for q in page['areas'] if q['label'] == 'body']:
                        if not helpers.rectangles_intersect(expanded, body):
                            valid = True
                            break

                if not valid:
                    area['label'] = 'unknown'
    return pages
