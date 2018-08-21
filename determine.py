from psycopg2.extensions import AsIs
import psycopg2.extras
import numpy as np
from sklearn import svm

# Connect to Postgres
connection = psycopg2.connect(dbname='ocr-classify', user='john', host='localhost', port='5432')
#cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cursor = connection.cursor()

cursor.execute("""
    SELECT
        a.area_id,
        ad.doc_id,
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
        proportion_alpha,
        area::float / (select max(area) from areas) as area,
        n_gaps::float / (select max(n_gaps) from areas) as n_gaps,
        n_lines::float / (select max(n_lines) from areas) as n_lines,
        page_no::float / (select max(page_no) from areas z join area_docs x on z.area_id=x.area_id where x.doc_id = ad.doc_id)
    FROM areas a
    JOIN area_docs ad ON a.area_id = ad.area_id
    JOIN area_labels al ON al.area_id = a.area_id
    JOIN labels ON labels.label_id = al.label_id
    WHERE a.area_id NOT IN (
        527,1252,56,153,1454,1072,1154,1514,207,1269,89,1684,102,66,560,972,858,280,1425,1071,759,787,1451,1172,1576,552,831,926,1262,901,1233,1415,1695,464,316,1397,746,1663,1366,492,967,1627,1617,205,1643,876,1630,441,1651,1657
    )
""")
data = cursor.fetchall()

# Omit area_id, doc_id, page_no, and label_name
train = [ list(d[4:]) for d in data ]

label = np.array([ d[3] for d in data ])
index = [ d[0:3] for d in data ]

# gamma - influence of a single training example. low = far, high = close
# C - low = less freedom, high = more freedom
clf = svm.SVC(gamma=1, C=100, probability=True, cache_size=500, kernel='rbf')

clf.fit(train, label)


cursor.execute("""
    SELECT
        a.area_id,
        ad.doc_id,
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
        proportion_alpha,
        area::float / (select max(area) from areas) as area,
        n_gaps::float / (select max(n_gaps) from areas) as n_gaps,
        n_lines::float / (select max(n_lines) from areas) as n_lines,
        page_no::float / (select max(page_no) from areas z join area_docs x on z.area_id=x.area_id where x.doc_id = ad.doc_id)
    FROM areas a
    JOIN area_docs ad ON a.area_id = ad.area_id
    JOIN area_labels al ON al.area_id = a.area_id
    JOIN labels ON labels.label_id = al.label_id
    WHERE a.area_id IN (
        527,1252,56,153,1454,1072,1154,1514,207,1269,89,1684,102,66,560,972,858,280,1425,1071,759,787,1451,1172,1576,552,831,926,1262,901,1233,1415,1695,464,316,1397,746,1663,1366,492,967,1627,1617,205,1643,876,1630,441,1651,1657
    )
""")
data = cursor.fetchall()

groups = {}

for cat in clf.classes_:
    groups[cat] = {
        'p': [],
        'label': []
    }

for area in data:
    classification_p = clf.predict_proba([list(area[4:])])
    classification_label = clf.predict([list(area[4:])])
    named_p = zip(clf.classes_, classification_p[0])

    groups[area[3]]['label'].append( 1 if classification_label[0] == area[3] else 0 )

    for each in named_p:
        if each[0] == area[3]:
            groups[area[3]]['p'].append(each[1])

for cat in groups:
    print(cat)
    print('   + p (avg) ', (sum(groups[cat]['p']) / len(groups[cat]['p'])))
    print('   + correct ', (sum(groups[cat]['label']) / float(len(groups[cat]['label']))) * 100, '%')

print('TOTAL')
print('   + p (avg) ', sum([ val for val in groups[cat]['p'] for cat in groups ]) / len([ val for val in groups[cat]['p'] for cat in groups ]))
print('   + correct ', sum([ val for val in groups[cat]['label'] for cat in groups ]) / float(60) * 100, '%')
