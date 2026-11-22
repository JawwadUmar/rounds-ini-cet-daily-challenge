"""Build INICET TypeScript modules from the paired text and figure extracts."""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "src/data/pyq"
CACHE = ROOT / ".cache"
read = lambda p: json.loads(p.read_text(encoding="utf8"))
raw = read(CACHE / "pyq-raw.json")
images = read(CACHE / "pyq-assets.json")

SUBJECTS = (
    "Anatomy", "Physiology", "Biochemistry", "Pathology", "Pharmacology",
    "Microbiology", "Forensic Medicine", "PSM", "ENT", "Ophthalmology",
    "General Medicine", "General Surgery", "Obstetrics & Gynaecology",
    "Pediatrics", "Orthopedics", "Dermatology", "Psychiatry", "Radiology", "Anesthesia",
)
ALIASES = {
    "ANATOMY": "Anatomy", "PHYSIOLOGY": "Physiology", "BIOCHEMISTRY": "Biochemistry",
    "PATHOLOGY": "Pathology", "PHARMACOLOGY": "Pharmacology", "MICROBIOLOGY": "Microbiology",
    "FORENSIC MEDICINE": "Forensic Medicine", "PSM": "PSM", "ENT": "ENT",
    "OPHTHALMOLOGY": "Ophthalmology", "MEDICINE": "General Medicine", "SURGERY": "General Surgery",
    "OBS & GYNE": "Obstetrics & Gynaecology", "PEDIATRICS": "Pediatrics",
    "ORTHOPEDIC": "Orthopedics", "ORTHOPEDICS": "Orthopedics", "DERMATOLOGY": "Dermatology",
    "PSYCHIATRY": "Psychiatry", "RADIOLOGY": "Radiology", "ANAESTHESIA": "Anesthesia",
}
PAPERS = sorted({r["paper"] for r in raw}, key=lambda p: (-int(p.split("-")[1]), 0 if p.startswith("MAY-") else 1))
YEARS = sorted({r["year"] for r in raw}, reverse=True)
daily = defaultdict(lambda: defaultdict(list))
paper_sections = defaultdict(list)
read_only = set()
figure_count = 0

for r in raw:
    year, number, id_ = r["year"], r["number"], r["id"]
    subject = ALIASES.get(r["subjectHeading"].strip().upper())
    assert subject in SUBJECTS, (id_, r["subjectHeading"])
    assert r["id"] == f"pyq-{year}-{number}"
    assert all(r["options"].get(k, "").strip() for k in "ABCD") and len(r["options"]) == 4, id_
    key = re.match(r"^\(([ABCD])\)", r["answerText"])
    assert key and r["statement"].strip() and r["explanation"].strip(), id_
    session = r["paper"].replace("-", " ").title()
    entry = dict(
        number=number,
        printedNumber=r["printedNumber"],
        paperSession=session,
        statement=r["statement"],
        options=[r["options"][k] for k in "ABCD"],
        correct=key[1],
        answerText=r["answerText"],
        explanation=r["explanation"],
        pages=[r["page"], r["solutionPage"]],
        difficulty="Medium",
        difficultyEstimated=True,
        topic=subject,
    )
    if id_ in images:
        entry["images"] = [{k: im[k] for k in ("src", "width", "height", "alt")} for im in images[id_]]
        figure_count += len(entry["images"])
    if r.get("visualChoices"):
        entry["reviewOnly"] = True
        read_only.add(id_)
        if id_ not in images:
            entry["imageUnavailable"] = True
    if len(set(r["options"].values())) != 4 or any(c in "".join((r["statement"], r["answerText"], r["explanation"])) for c in ("\ufffd", "ï¿½")):
        entry["reviewOnly"] = True
        read_only.add(id_)
    daily[year][subject].append(entry)
    paper_sections[r["paper"]].append((r["printedNumber"], subject, number))

assert len({r["id"] for r in raw}) == len(raw)
assert len(images) <= len(raw) and sum(map(len, images.values())) == figure_count
assert set(ALIASES.values()) == set(SUBJECTS)

# Retain the subject transitions in printed question order for paper audits,
# and shift each sitting into its unique year-wide library-number range.
subject_ranges = {}
subject_years = defaultdict(lambda: defaultdict(list))
for paper in PAPERS:
    year = int(paper.split("-")[1])
    items = sorted(paper_sections[paper])
    starts = []
    previous = None
    for printed_number, subject, library_number in items:
        if subject != previous:
            starts.append([printed_number, subject])
            previous = subject
    subject_ranges.setdefault(str(year), {})[paper] = starts
    for index, (printed_start, subject) in enumerate(starts):
        first = next(number for n, s, number in items if n == printed_start and s == subject)
        end_printed = starts[index + 1][0] - 1 if index + 1 < len(starts) else items[-1][0]
        end = next(number for n, _, number in items if n == end_printed)
        subject_years[subject][year].append([first, end])

dump = lambda value: json.dumps(value, ensure_ascii=False, indent=2)
OUT.mkdir(exist_ok=True, parents=True)
header = "// Generated from the supplied INICET edition by scripts/pyq/populate.py.\n"
daily_data = ",\n".join(f"  ...readPaper({year}, {dump(groups)})" for year, groups in daily.items())
(OUT / "daily.ts").write_text(
    header + "import { readPaper } from './paper';\n\nexport const dailyPapers = [\n" + daily_data + "\n];\n",
    encoding="utf8",
)
for year in YEARS:
    (OUT / f"{year}.ts").write_text(
        header + "import { readPaper } from './paper';\nimport { dailyPapers } from './daily';\n\n"
        + f"const entries = readPaper({year}, {{}});\n"
        + f"export default [...entries, ...dailyPapers.filter(q => q.examYear === {year})].sort((a, b) => a.number! - b.number!);\n",
        encoding="utf8",
    )

subject_dir = OUT / "subjects"
subject_dir.mkdir(exist_ok=True)
imports, registry = [], []
for subject in SUBJECTS:
    slug = re.sub("[^a-z]+", "-", subject.lower()).strip("-")
    name = slug.replace("-", "_")
    years = subject_years[subject]
    lines = ",\n".join(f"  {year}: {json.dumps(years.get(year, []))}" for year in YEARS)
    (subject_dir / f"{slug}.ts").write_text(header + "export default {\n" + lines + "\n};\n", encoding="utf8")
    imports.append(f"import {name} from './subjects/{slug}';")
    registry.append(f"  {json.dumps(subject)}: {name}")
(OUT / "subject-index.ts").write_text(
    header + "import type { Subject } from '../types';\nimport type { PaperYear } from './index';\n"
    + "\n".join(imports) + "\n\nexport const subjectIndex: Record<Subject, Record<PaperYear, number[][]>> = {\n"
    + ",\n".join(registry) + "\n};\n",
    encoding="utf8",
)
(Path(__file__).with_name("subject-ranges.json")).write_text(
    json.dumps(subject_ranges, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
)
print(f"{len(raw)} questions across {len(PAPERS)} sittings; {figure_count} figures; {len(read_only)} read-only entries")
