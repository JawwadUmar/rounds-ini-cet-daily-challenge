"""Read the supplied MEDINK INICET edition, keeping question and answer keys paired.

Usage: python scripts/pyq/extract.py <pdf> [--out .cache/pyq-raw.json]
Requires PyMuPDF. The optional checkout-local installation is for authoring only.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".cache/pdf-tools").resolve()))
import pymupdf

EDITION_SHA256 = "fd867ae63f19f7d245070a5ac9a1c8e822a9ddf8e8d5e92d84f14df83d805a14"
NUM_COLOR = 0x171717
WHITE = 0xFFFFFF
CHOICE = re.compile(r"^\(([A-E])\)\s*")
SUBSCRIPT = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")
SUPERSCRIPT = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def number(span):
    if span["color"] == NUM_COLOR and re.fullmatch(r"\d+\.", span["text"].strip()):
        return int(span["text"].strip()[:-1])
    return None


def merge_lines(spans, preserve_paragraphs=False):
    """Rejoin typesetter wraps while retaining list, table, and paragraph boundaries."""
    rows = []
    for span in spans:
        if not span["text"].strip():
            continue
        first = rows[-1][0] if rows else None
        if first and span["page"] == first["page"] and (first["origin"][0]<288) == (span["origin"][0]<288) and abs(span["origin"][1]-first["origin"][1]) < max(span["size"],first["size"])*.64:
            rows[-1].append(span)
        else:
            rows.append([span])
    lines = []
    for row in rows:
        normal = max(row, key=lambda s:s["size"])
        previous, line = None, ""
        for s in sorted(row, key=lambda s:s["origin"][0]):
            word = s["text"].replace("\x01","�")
            if s["font"] == "MMaArrow-Regular":
                word = word.replace('"',"→")
            if s["size"] < normal["size"]*.80 and re.fullmatch(r"[0-9+−-]+",word.strip()):
                offset = s["origin"][1] - normal["origin"][1]
                word = word.strip().replace("−","-").translate(SUBSCRIPT if offset>0 else SUPERSCRIPT)
            gap = s["origin"][0] - previous["bbox"][2] if previous else 0
            space = previous and (gap>normal["size"]*.11 or previous["text"].endswith(" ") or s["text"].startswith(" "))
            line += (" " if space else "") + word.strip()
            previous = s
        lines.append(line)
    if preserve_paragraphs:
        return "\n".join(lines).strip()
    result = ""
    for line in lines:
        new_line = bool(re.match(r"^(?:\d+[.)]|[A-Ea-e][.)]|[ivx]+[.)]|[•●▪])\s", line))
        join = "\n" if new_line else ("" if result.endswith("-") else " ")
        result += (join if result else "") + line
    return result.strip()


def pages_by_section(doc):
    """Identify the ten paper sittings from their repeated running titles.

    Question and answer sheets are physically interleaved. The tiny white
    answer layer marks question sheets; printed answer sheets use normal text.
    Each physical sheet still has a consecutive question-number run, so sheets
    can be sorted into logical order by their first anchor.
    """
    sections = collections.defaultdict(list)
    for page in doc:
        spans = [s for b in page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
                 if b["type"] == 0 for line in b["lines"] for s in line["spans"]
                 if s["text"].strip() and s["font"] != "Helvetica-Bold" and s["origin"][1] >= 55
                 and not re.fullmatch(r"\*+", s["text"].strip())]
        nums = [n for s in spans if (n := number(s)) is not None]
        if not nums:
            continue
        page_no = page.number + 1
        if nums != list(range(nums[0], nums[-1] + 1)):
            raise ValueError(f"Broken anchors on page {page_no}")
        labels = set(re.findall(r"EXAMINATION PAPER\s+((?:MAY|NOV)[- ]?20\d{2})", page.get_text(), re.I))
        if len(labels) != 1:
            raise ValueError(f"Cannot identify the paper sitting on page {page_no}: {sorted(labels)}")
        paper = re.sub(r"[- ]", "-", labels.pop().upper())
        section = "questions" if any(s["color"] == WHITE and abs(s["size"] - .25) < .01 for s in spans) else "solutions"
        content = [dict(s, page=page_no) for s in spans if s["size"] < 23 and not re.fullmatch(
            r"(?:page\s*\d+|INICET Examination Paper|MEDINK|EXAMINATION PAPER\s+(?:MAY|NOV)[- ]?20\d{2})",
            s["text"].strip(), re.I)]
        sections[paper, section].append((nums[0], content))
    result = {}
    for (paper, section), sheets in sections.items():
        ordered = sorted(sheets)
        for _, sheet in ordered:
            sheet_nums = [n for s in sheet if (n := number(s)) is not None]
            if sheet_nums != list(range(sheet_nums[0], sheet_nums[-1] + 1)):
                raise ValueError(f"Broken {paper} {section} sheet")
        result[paper, section] = [span for _, sheet in ordered for span in sheet]
    return result


def question_blocks(spans):
    result, subject, current = {}, "", None
    for s in spans:
        if round(s["size"]) == 16 and s["color"] != WHITE:
            subject = s["text"].strip()
        elif (n := number(s)) is not None:
            current = {"subjectHeading": subject, "page": s["page"], "origin": s["origin"], "visible": [], "answer": []}
            result[n] = current
        elif current is not None:
            current["answer" if s["color"] == WHITE else "visible"].append(s)
    return result


def solution_blocks(spans):
    result, question, answer = {}, [], None
    for s in spans:
        if (n := number(s)) is not None:
            answer = []
            result[n] = (question, answer, s["page"])
            question = []
        elif s["color"] == WHITE:
            question.append(s)
        elif answer is not None:
            answer.append(s)
    return result


def split_choices(spans):
    groups = {"statement": []}
    section = "statement"
    for s in spans:
        word = s["text"].lstrip()
        marker = CHOICE.match(word)
        if marker and marker[1] not in groups:
            section = marker[1]
            groups[section] = []
            s = {**s, "text": word[marker.end():]}
        groups[section].append(s)
    fields = {field: merge_lines(parts) for field, parts in groups.items()}
    if not all(k in fields for k in "ABCD"):
        # Several printed papers lay two options side by side inside one text span.
        for label, value in list(fields.items()):
            if label == "statement":
                continue
            parts = re.split(r"\s+\(([A-D])\)\s*",value)
            fields[label] = parts[0].strip()
            for letter, text in zip(parts[1::2], parts[2::2]):
                fields[letter] = text.strip()
    return fields


def compact(text):
    return re.sub(r"\s+", "", text)


def printed_solution(spans, option_text):
    full = merge_lines(spans)
    marker = CHOICE.match(full)
    if not marker:
        raise ValueError("Printed solution has no letter: " + full[:60])
    key = marker.group().strip()
    text = full[marker.end():].lstrip()
    option = option_text.get(marker[1], "").strip()
    if option:
        pattern = r"\s*".join(map(re.escape,compact(option)))
        match = re.match(pattern,text,re.I)
        if match:
            return key+" "+text[:match.end()], text[match.end():].lstrip()
    return key, text


def split_key(spans):
    spans = [s for s in spans if not re.fullmatch(r"A?Ans\s*:?\s*|\x01", s["text"].strip(), re.I)]
    if not spans:
        return "", ""
    # The compressed answer text retains paragraph baselines; a long keyed answer can wrap.
    key, body = [], []
    for s in spans:
        if not key or (not body and abs(s["origin"][1] - key[0]["origin"][1]) < key[0]["size"]*.64 and s["page"] == key[0]["page"]):
            key.append(s)
        else:
            body.append(s)
    return merge_lines(key), merge_lines(body, preserve_paragraphs=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path, default=Path(".cache/pyq-raw.json"))
    args = parser.parse_args()
    fingerprint = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    if fingerprint != EDITION_SHA256:
        raise ValueError("This extractor targets the supplied MEDINK INICET edition.")
    with pymupdf.open(args.pdf) as doc:
        if len(doc) != 754:
            raise ValueError("The supplied INICET edition has 754 physical pages.")
        sections = pages_by_section(doc)
    papers = sorted({paper for paper, section in sections if section == "questions"},
                    key=lambda p: (-int(p.split("-")[1]), 0 if p.startswith("MAY-") else 1))
    raw, audit, anchors = [], [], []
    year_offsets = collections.defaultdict(int)
    for paper in papers:
        period, year_text = paper.split("-")
        year = int(year_text)
        questions = question_blocks(sections[paper, "questions"])
        solutions = solution_blocks(sections.get((paper, "solutions"), []))
        if not questions or sorted(questions) != list(range(1, max(questions) + 1)):
            raise ValueError(f"Incomplete question sequence for {paper}")
        if set(solutions) - set(questions):
            raise ValueError(f"Answer sheet has unmatched questions for {paper}")
        offset = year_offsets[year]
        for n, item in questions.items():
            library_number = offset + n
            key = f"pyq-{year}-{library_number}"
            # The May 2022 question section repeats question 67 at 68. Its
            # solution section has 199 entries, so question 69 onward pairs
            # with the preceding printed solution number.
            solution_number = (None if paper == "MAY-2022" and n == 68 else
                               n - 1 if paper == "MAY-2022" and n >= 69 else n)
            check, printed, solution_page = solutions.get(solution_number, ([], [], item["page"]))
            primary = split_choices(item["visible"])
            secondary = split_choices(check)
            statement = primary.get("statement", "").strip()
            options = {letter: primary.get(letter, "").strip() for letter in "ABCD"}
            secondary_statement = secondary.get("statement", "").strip()
            secondary_options = {letter: secondary.get(letter, "").strip() for letter in "ABCD"}
            visual_choices = (paper, n) in {
                ("MAY-2022", 67), ("MAY-2022", 68), ("NOV-2020", 12),
            }
            if (not visual_choices and (not statement or not all(options.values()))
                    and secondary_statement and all(secondary_options.values())):
                statement, options = secondary_statement, secondary_options
            else:
                for letter in "ABCD":
                    if not options[letter] and secondary_options[letter]:
                        options[letter] = secondary_options[letter]

            # These questions print their answer choices as labelled figures.
            # The app keeps the four-choice schema and shows the extracted figures.
            if (paper, n) in {("MAY-2022", 67), ("MAY-2022", 68)}:
                options = {letter: f"Figure {letter}" for letter in "ABCD"}
            elif (paper, n) == ("NOV-2020", 12):
                options = {letter: f"Image {letter}" for letter in "ABCD"}
            if (paper, n) == ("MAY-2023", 173):
                options["C"] = "Seborrheic dermatitis"
            answer_text, explanation = split_key(item["answer"])
            solution = merge_lines(printed)
            if solution_number in solutions and compact(answer_text+explanation) != compact(solution):
                printed_key, printed_explanation = printed_solution(printed, options)
                answer_text, explanation = printed_key, printed_explanation
            if visual_choices and re.fullmatch(r"\([ABCD]\)", answer_text):
                key_letter = answer_text[1]
                answer_text = f"{answer_text} {options[key_letter]}"
            if not answer_text or not explanation:
                raise ValueError(f"Missing answer or explanation for {paper} question {n}")
            audit.append(dict(id=key, paper=paper, printedNumber=n, solutionNumber=solution_number, secondary=secondary,
                              printed=solution, hiddenAnswer=merge_lines(item["answer"],True)))
            raw.append(dict(id=key,year=year,paper=paper,printedNumber=n,number=library_number,
                            subjectHeading=item["subjectHeading"],page=item["page"],solutionPage=solution_page,
                            statement=statement,options=options,visualChoices=visual_choices,
                            answerText=answer_text,explanation=explanation))
            anchors.append(dict(id=key,year=year,paper=paper,number=library_number,printedNumber=n,
                                page=item["page"],origin=item["origin"]))
        year_offsets[year] += max(questions)
        print(f"{paper}: {len(questions)} questions; {len(solutions)} printed solutions")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    for path, data in [(args.out,raw),(args.out.with_name("pyq-crosscheck.json"),audit),(args.out.with_name("pyq-anchors.json"),anchors)]:
        path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    print(f"{len(raw)} numbered questions across {len(papers)} sittings, PDF SHA-256 {fingerprint}")


if __name__ == "__main__":
    main()
