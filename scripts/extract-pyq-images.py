"""Extract INICET question figures and pair them with printed question anchors.

The paired text extraction writes .cache/pyq-anchors.json first. Image paths are
grouped by year and May/November sitting to keep independently numbered papers
separate. Physical PDF pages are one-based.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(".cache/pdf-tools").resolve()))
import pymupdf


EDITION_SHA256 = "fd867ae63f19f7d245070a5ac9a1c8e822a9ddf8e8d5e92d84f14df83d805a14"
QR_SIZES = {(74, 74), (57, 57)}
TEXT_FLAGS = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES


@dataclass(frozen=True)
class Anchor:
    id: str
    page: int
    number: int
    printed_number: int
    year: int
    paper: str
    column: int
    baseline: float


def column(x):
    return 0 if x < 288 else 1


def read_anchors(path):
    rows = json.loads(path.read_text(encoding="utf8"))
    locations, pages = {}, defaultdict(list)
    for row in rows:
        x, baseline = row["origin"]
        anchor = Anchor(row["id"], row["page"], row["number"], row["printedNumber"],
                        row["year"], row["paper"], column(x), baseline)
        key = (anchor.paper, anchor.printed_number)
        if key in locations:
            raise ValueError(f"Duplicate printed question anchor {key}")
        locations[key] = anchor
        pages[anchor.page].append(anchor)
    for anchors in pages.values():
        anchors.sort(key=lambda a: (a.column, a.baseline))
    return locations, pages


def extract_image(document, xref):
    image = document.extract_image(xref)
    extension = {"jpeg": "jpg", "jpg": "jpg", "png": "png"}.get(image["ext"])
    if extension:
        return image["image"], extension, image["width"], image["height"]
    pixmap = pymupdf.Pixmap(document, xref)
    if pixmap.alpha or pixmap.n > 3:
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
    return pixmap.tobytes("png"), "png", pixmap.width, pixmap.height


def extract(pdf, public_dir, map_path, anchor_path):
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != EDITION_SHA256:
        raise ValueError("This image layout belongs to the supplied MEDINK INICET edition")
    locations, anchors_by_page = read_anchors(anchor_path)
    groups = defaultdict(list)
    skipped_before_first = 0
    with pymupdf.open(pdf) as document:
        if len(document) != 754:
            raise ValueError("The supplied INICET edition has 754 physical pages")
        for page_number, anchors in anchors_by_page.items():
            page = document[page_number - 1]
            seen_xrefs = set()
            for xref, _, width, height, *_ in page.get_images(full=True):
                if (width, height) in QR_SIZES:
                    continue
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                boxes = page.get_image_rects(xref)
                for box in boxes:
                    position = (column((box.x0 + box.x1) / 2), (box.y0 + box.y1) / 2)
                    before = [a for a in anchors if (a.column, a.baseline) <= position]
                    if before:
                        owner = before[-1]
                    else:
                        previous_number = anchors[0].printed_number - 1
                        owner = locations.get((anchors[0].paper, previous_number))
                        if owner is None:
                            skipped_before_first += 1
                            continue
                    groups[owner.id].append({
                        "page": page_number,
                        "bbox": [round(v, 3) for v in box],
                        "xref": xref,
                        "year": owner.year,
                        "paper": owner.paper,
                        "printedNumber": owner.printed_number,
                        "width": width,
                        "height": height,
                    })

        mapping = {}
        for question_id, items in sorted(groups.items()):
            items.sort(key=lambda item: (item["page"], round(item["bbox"][1] / 2), item["bbox"][0]))
            count = len(items)
            for index, item in enumerate(items, 1):
                image, extension, image_width, image_height = extract_image(document, item["xref"])
                if (image_width, image_height) != (item["width"], item["height"]):
                    raise ValueError(f"Intrinsic image dimensions changed for {question_id}")
                sitting = item["paper"].lower()
                src = f"assets/images/pyq/{item['year']}/{sitting}/q{item['printedNumber']}-{index}.{extension}"
                output_path = public_dir / src
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image)
                item.update(src=src, alt="Figure accompanying the question" if count == 1
                            else f"Question figure {index} of {count}", role="question")
            mapping[question_id] = items

        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    figure_count = sum(map(len, mapping.values()))
    print(f"Extracted {figure_count} figures for {len(mapping)} questions; skipped {skipped_before_first} pre-question placements")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--public", type=Path, default=Path("public"))
    parser.add_argument("--map", type=Path, default=Path(".cache/pyq-assets.json"))
    parser.add_argument("--anchors", type=Path, default=Path(".cache/pyq-anchors.json"))
    args = parser.parse_args()
    extract(args.pdf, args.public, args.map, args.anchors)
