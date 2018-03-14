import sys
import glob
from bs4 import BeautifulSoup
import helpers

import matplotlib.pyplot as plt
import matplotlib.patches as patches

def merge_areas(areas):
    def process(soup):
        # Given a tesseract title string, extract the bounding box coordinates
        title = soup.get('title')
        for part in title.split(';'):
            if part.strip()[0:4] == 'bbox':
                bbox = part.replace('bbox', '').strip().split()
                return {
                    'x1': int(bbox[0]),
                    'y1': int(bbox[1]),
                    'x2': int(bbox[2]),
                    'y2': int(bbox[3]),
                    'soup': soup
                }
        return {}

    areas = [ process(area) for area in areas ]
    merged = group_areas(areas)

    last_length = len(areas)
    current_length = len(merged)
    c = 0
    while current_length < last_length:
        c += 1
        # Check yo self before you wreck yoself
        if c > 20:
            break
        last_length = len(merged)
        merged = group_areas(merged)
        current_length = len(merged)

    return merged




def group_areas(areas):
    def rectangles_intersect(a, b):
        pad = 1
        a['x1'] -= pad
        b['x2'] += pad

        # Determine whether or not two rectangles intersect
        if (a['x1'] < b['x2']) and (a['x2'] > b['x1']) and (a['y1'] < b['y2']) and (a['y2'] > b['y1']):
            return True
        else:
            return False

    grouped_areas = []

    for area in areas:
        found = False
        for idx, ga in enumerate(grouped_areas):
            if rectangles_intersect(ga, area):
                grouped_areas[idx]['soup'] = BeautifulSoup(str(area['soup']) + str(grouped_areas[idx]['soup']), 'html.parser')
                grouped_areas[idx].update(helpers.enlarge_extract(ga, area))
                found = True
                break

        if not found:
            grouped_areas.append(area)

    return grouped_areas




with open('./docs/871/tesseract/page_11.html') as hocr:
    text = hocr.read()
    soup = BeautifulSoup(text, 'html.parser')

merged = merge_areas(soup.find_all('div', 'ocr_carea'))

print helpers.area_summary(merged[3])


fig = plt.figure()
ax = fig.add_subplot(111, aspect='equal')

for area in merged:
    ax.add_patch(patches.Rectangle(
            (area['x1'], area['y1']),
            area['x2'] - area['x1'],
            area['y2'] - area['y1'],
            fill=False,
            linewidth=0.75,
            edgecolor="blue"
            ))

plt.ylim(min([ area['y1'] for area in merged ]),max([ area['y2'] for area in merged ]))
plt.xlim(min([ area['x1'] for area in merged ]),max([ area['x2'] for area in merged ]))
ax = plt.gca()
ax.invert_yaxis()
plt.axis('off')
plt.show()
