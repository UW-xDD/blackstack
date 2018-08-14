CREATE TABLE areas (
    area_id serial not null,
    page_no integer,
    has_words boolean,
    line_intersect boolean,
    small_text boolean,
    small_leading boolean,
    is_line boolean,
    is_top_or_bottom boolean,
    mostly_blank boolean,
    very_separated_words boolean,
    little_word_coverage boolean,
    normal_word_separation boolean,
    normal_word_coverage boolean,
    best_caption boolean,
    good_caption boolean,
    ok_caption boolean,
    overlap boolean,
    proportion_alpha numeric,
    offset_words boolean,
    n_gaps integer,
    n_lines integer,
    x1 integer,
    y1 integer,
    x2 integer,
    y2 integer,
    area numeric
);

CREATE INDEX ON areas (area_id);

CREATE TABLE area_docs (
  area_id integer not null,
  doc_id text
);
CREATE INDEX ON area_docs (area_id);
CREATE INDEX ON area_docs (doc_id);

CREATE TABLE labels (
    label_id serial not null,
    name text not null
);
CREATE INDEX ON labels (label_id);

INSERT INTO labels (name) VALUES ('header / footer'), ('body'), ('graphic'), ('graphic caption'), ('reference'), ('other');

CREATE TABLE area_labels (
    area_id integer not null,
    label_id integer not null,
    unique (area_id, label_id)
);
CREATE INDEX ON area_labels (area_id);
CREATE INDEX ON area_labels (label_id);
