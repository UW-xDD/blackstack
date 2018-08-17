import sys
import os
from flask import Flask, request, make_response, render_template, send_file
import logging
from PIL import Image
import string
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from sklearn import svm

# Import database credentials
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from config import Credentials

def random_name():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))

# Create the Flask app
app = Flask(__name__)

# Set up logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Connect to Postgres
connection = psycopg2.connect(
    dbname=Credentials.PG_DATABASE,
    user=Credentials.PG_USERNAME,
    password=Credentials.PG_PASSWORD,
    host=Credentials.PG_HOST,
    port=Credentials.PG_PORT
)
cursor = connection.cursor()


def random_area():
    cursor.execute("""
      SELECT areas.area_id, doc_id, page_no, x1, y1, x2, y2,
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
      FROM areas
      JOIN area_docs ON areas.area_id = area_docs.area_id
      LEFT JOIN area_labels ON area_labels.area_id = areas.area_id
      WHERE area > 100000 AND label_id IS NULL
      ORDER BY random()
      LIMIT 1
    """)
    area = cursor.fetchall()[0]
    q = list(area[7:])

    estimated_label = clf.predict([q])[0]

    p = zip(clf.classes_, clf.predict_proba([q])[0])

    bad = False
    for each in p:
        if each[0] == estimated_label and each[1] > 0.9:
            bad = True

    if bad:
        return random_area()

    new_area = {
        'area_id': area[0],
        'doc_id': area[1],
        'page_no': area[2],
        'x1': area[3],
        'y1': area[4],
        'x2': area[5],
        'y2': area[6]
    }

    for each in p:
        new_area[each[0]] = each[1]

    new_area['img'] = get_area_image(area[1], area[2], { 'x1': area[3], 'y1': area[4], 'x2': area[5], 'y2': area[6] })
    return new_area


# def get_area(area_id):
#     cursor.execute("""
#       SELECT areas.area_id, doc_id, page_no, x1, y1, x2, y2
#       FROM areas
#       JOIN area_docs ON areas.area_id = area_docs.area_id
#       WHERE areas.area_id = %(area_id)s
#     """, { "area_id": area_id })
#     area = cursor.fetchone()
#     area['img'] = get_area_image(area['doc_id'], area['page_no'], { 'x1': area['x1'], 'y1': area['y1'], 'x2': area['x2'], 'y2': area['y2'] })
#     return area


def get_area_image(doc, page, extract):
    img_name = random_name()
    image = np.array(Image.open('../docs/%s/png/page_%s.png' % (doc, page)), dtype=np.uint8)
    fig,ax = plt.subplots(1)
    ax.imshow(image)
    ax.add_patch(patches.Rectangle(
            (extract['x1'], extract['y1']),
            extract['x2'] - extract['x1'],
            extract['y2'] - extract['y1'],
            fill=False,
            linewidth=1.5,
            edgecolor="#D90000"
            )
            )

    plt.axis('off')
    fig.savefig('tmp/' + img_name + '.png', dpi=200, bbox_inches='tight', pad_inches=0)
    plt.close(fig)

    # image.crop((extract['x1'], extract['y1'], extract['x2'], extract['y2'])).save('tmp/' + img_name + '.png', 'png')
    return img_name

def add_label(label_id, area_id):
    cursor.execute("""
        INSERT INTO area_labels (area_id, label_id)
        VALUES (%(area_id)s, %(label_id)s)
    """, { "label_id": label_id, "area_id": area_id })
    connection.commit()

    return ('', 200)


@app.route('/')
# @app.route('/<a>')
def default():
    # if a is None:
    area = random_area()
    # else:
    #     print a
    #     area = get_area(a)

    return render_template('index.html', area_id=area['area_id'], img=area['img'], doc_id=area['doc_id'], page_no=area['page_no'], body=area['body'], graphic=area['graphic'], graphic_caption=area['graphic caption'], header_footer=area['header / footer'], reference=area['reference'])

@app.route('/tmp/<img>')
def send_img(img=None):
    if img is not None:
        return send_file('./tmp/' + img, mimetype='image/png')
    else:
        send_file(None)

@app.route('/label', methods=['POST'])
def learn():
    # Need an area_id and a
    return add_label(request.form['label_id'], request.form['area_id'])


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
index = [ d[0:3] for d in data ]

# gamma - influence of a single training example. low = far, high = close
# C - low = less freedom, high = more freedom
#clf = svm.SVC(gamma=0.001, C=100., probability=True, cache_size=500)
clf = svm.SVC(gamma=1, C=100, probability=True, cache_size=500, kernel='rbf')

clf.fit(train, label)

# print clf.classes_

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)
