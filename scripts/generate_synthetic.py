#!/usr/bin/env python3
"""Generate deterministic training candidates with source-exact A/B/C labels.

These are synthetic training pages, never substitutes for reviewed real tests.
"""
import argparse
from datetime import date
import hashlib
from html import escape
from io import BytesIO
import json
from pathlib import Path
import random
import platform
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import PIL


def generation_metadata(seed, count, font_path):
    return {"seed": seed, "count": count, "python": platform.python_version(),
            "pillow": PIL.__version__, "numpy": np.__version__,
            "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
            "status": "training_candidates_not_a_test_release"}


def generate(index, seed, font_path):
    rng = random.Random(seed + index)
    kind = ("invoice", "contract", "letter", "form")[index % 4]
    sample_id = f"syn_{seed}_{index:05d}"
    image = Image.new("L", (1040, 1471), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), 19)
    heading = ImageFont.truetype(str(font_path), 28)
    small = ImageFont.truetype(str(font_path), 16)
    y = 75
    markdown = []
    when = date(2026, rng.randint(1, 12), rng.randint(1, 28))
    number = f"TEST/{index+1:05d}/{when.year}"
    unit = f"Instytucja Testowa {rng.choice(['Żuraw', 'Łąka', 'Źródło', 'Gęś', 'Świerk', 'Ćma'])} {rng.randint(1,99)}"
    amount = rng.randint(10000, 900000)
    money = f"{amount//100},{amount%100:02d} PLN"
    titles = {"invoice": "Faktura testowa", "contract": "Umowa testowa", "letter": "Pismo urzędowe — przykład", "form": "Formularz testowy"}
    title = titles[kind] + " " + number

    def line(text, style="body"):
        nonlocal y
        active_font = heading if style == "heading" else font
        width = 53 if style == "heading" else 79
        for fragment in textwrap.wrap(text, width=width, break_long_words=False) or [""]:
            if y > 1330:
                raise ValueError(f"Page overflow: {sample_id}")
            draw.text((72, y), fragment, font=active_font, fill=25)
            y += 39 if style == "heading" else 30
        y += 12
        markdown.append(("# " if style == "heading" else "") + text)

    line(title, "heading")
    line(f"Data dokumentu: {when.strftime('%d.%m.%Y')}")
    line(f"Jednostka: {unit}")
    line(f"Znak sprawy: {number}")
    line("Adres: ul. Przykładowa 7/12, 00-000 Miasto Testowe")
    tables = None
    kie = {"document_date": when.isoformat(), "reference": number, "issuer": unit}
    field_types = {"document_date": "date", "reference": "identifier", "issuer": "text"}
    if kind in ("invoice", "form"):
        header = ["Pozycja", "Liczba", "Wartość PLN"]
        rows = []
        for item in range(rng.randint(3, 6)):
            label = rng.choice(["Obsługa zgłoszeń", "Przegląd załączników", "Archiwizacja akt", "Tłumaczenie pisma", "Zakup wyposażenia"])
            value = rng.randint(100, 90000)
            rows.append([f"{item+1}. {label}", str(rng.randint(1, 30)), f"{value//100},{value%100:02d}"])
        column_widths = [490, 135, 200]
        table_lines = ["| " + " | ".join(header) + " |", "| --- | --- | --- |"]
        for row_number, cells in enumerate([header, *rows]):
            x = 72
            for cell, width in zip(cells, column_widths):
                draw.rectangle((x, y, x+width, y+43), outline=100, fill=232 if row_number == 0 else 255)
                draw.text((x+9, y+9), cell, font=font, fill=20)
                x += width
            y += 43
            if row_number:
                table_lines.append("| " + " | ".join(cells) + " |")
        y += 32
        markdown.append("\n".join(table_lines))
        tables = ["<table><thead><tr>" + "".join(f"<th>{escape(c)}</th>" for c in header) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in rows) + "</tbody></table>"]
        # Explicit separate amount; individual table amounts are not claimed to sum
        # to this independent declared budget limit.
        line(f"Limit budżetu: {money}")
        kie["budget_limit"] = money
        field_types["budget_limit"] = "amount"
    else:
        subject = rng.choice(["udostępnienie informacji", "uzupełnienie dokumentacji", "rozliczenie projektu", "odbiór załączników", "termin odpowiedzi"])
        line(f"Przedmiot: {subject}")
        kie["subject"] = subject
        field_types["subject"] = "text"
        line("Niniejszy dokument zawiera wyłącznie fikcyjne informacje przygotowane na potrzeby uczenia rozpoznawania polskich dokumentów.")
        line(f"Prosimy o sprawdzenie pozycji oznaczonej numerem {rng.randint(1,99)} oraz zachowanie czytelnego układu pisma, nagłówków i znaków diakrytycznych.")
        line("Załączniki:")
        for item in rng.sample(["wykaz spraw", "zestawienie kosztów", "opis postępowania", "potwierdzenie odbioru"], 3):
            line("• " + item)
            markdown[-1] = "- " + item
    line("Uwagi: Zażółć gęślą jaźń. Rozróżnij ą, a, ł, l, ż oraz ź.")
    footer = "Dokument syntetyczny. Nie stanowi rzeczywistej faktury, umowy ani decyzji."
    draw.text((72, 1380), footer, font=small, fill=100)
    markdown.append(footer)
    degradation = ("scanner", "jpeg", "blur")[index % 3]
    params = {"mode": degradation}
    if degradation == "scanner":
        angle = rng.uniform(-1.1, 1.1)
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
        noise = np.random.default_rng(seed + index).normal(0, 2.2, (image.height, image.width))
        image = Image.fromarray(np.clip(np.asarray(image).astype(float) + noise, 0, 255).astype("uint8"))
        params.update(angle_degrees=angle, noise_sigma=2.2)
    elif degradation == "jpeg":
        quality = rng.randint(35, 65)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        image = Image.open(BytesIO(buffer.getvalue())).copy()
        params["jpeg_quality"] = quality
    else:
        radius = rng.uniform(.35, .75)
        image = image.filter(ImageFilter.GaussianBlur(radius))
        params["blur_radius"] = radius
    reference = {"id": sample_id, "text": "\n\n".join(markdown), "tables": tables, "kie": kie,
                 "field_types": field_types, "status": "programmatic", "split": "train", "reviewers": []}
    item = {"id": sample_id, "image": f"images/{sample_id}.png", "subtasks": ["A", "C"] + (["B"] if tables is not None else []),
            "document_type": kind, "kie_schema": field_types, "source": "synthetic", "license": "CC-BY-4.0", "degradation": params,
            "quality_status": "programmatic_training_candidate_visual_audit_pending"}
    return image, item, reference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--count", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--font", type=Path, default=Path(__file__).resolve().parents[1] / "assets/NotoSans-Regular.ttf")
    args = parser.parse_args()
    if args.count < 1:
        raise ValueError("Count must be positive")
    image_dir = args.output / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    args.references.parent.mkdir(parents=True, exist_ok=True)
    with (args.output / "inputs.jsonl").open("w") as inputs, args.references.open("w") as references:
        for i in range(args.count):
            image, item, reference = generate(i, args.seed, args.font)
            dest = args.output / item["image"]
            image.save(dest, compress_level=3)
            item["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
            inputs.write(json.dumps(item, ensure_ascii=False) + "\n")
            references.write(json.dumps(reference, ensure_ascii=False) + "\n")
            if (i+1) % 100 == 0:
                print(f"Generated {i+1}/{args.count} synthetic training candidates", flush=True)
    (args.output / "README.md").write_text("# Synthetic training candidates\n\nProgrammatically generated A/B/C training examples. Source-exact labels are separate. These are not real scanned documents, test sets, or manually verified annotations.\n\nCC BY 4.0; attribution: PolOCRBench organizers. Font: Noto Sans (SIL OFL).\n")
    (args.output / "generation-metadata.json").write_text(json.dumps(generation_metadata(args.seed, args.count, args.font), indent=2) + "\n")


if __name__ == "__main__":
    main()
