"""Deterministic text, table, and KIE scoring. No model judges."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata

from apted import APTED, Config
from lxml import etree, html
from rapidfuzz.distance import Levenshtein


def normalize_text(text):
    text = unicodedata.normalize("NFC", text)
    text = text.translate(str.maketrans({"„": '"', "“": '"', "”": '"', "«": '"', "»": '"', "‘": "'", "’": "'"}))
    return " ".join(text.split())


def text_counts(reference, prediction):
    ref, pred = normalize_text(reference), normalize_text(prediction)
    return {"char_edits": Levenshtein.distance(ref, pred), "reference_chars": len(ref),
            "word_edits": Levenshtein.distance(ref.split(), pred.split()), "reference_words": len(ref.split())}


def markdown_structure(text):
    tokens = []
    fenced = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("```"):
            tokens.append("fence")
            fenced = not fenced
        elif not fenced:
            if match := re.match(r"^(#{1,6})\s", line):
                tokens.append("heading" + str(len(match[1])))
            elif re.match(r"^[-*+]\s", line):
                tokens.append("bullet")
            elif re.match(r"^\d+[.)]\s", line):
                tokens.append("numbered")
            elif line.startswith("|"):
                tokens.append("table_row")
            elif line.startswith(">"):
                tokens.append("quote")
    return tokens


@dataclass
class TableNode:
    tag: str
    rowspan: int = 1
    colspan: int = 1
    content: tuple = ()
    children: list = field(default_factory=list)


class TableConfig(Config):
    def rename(self, first, second):
        if (first.tag, first.rowspan, first.colspan) != (second.tag, second.rowspan, second.colspan):
            return 1.0
        if first.tag in ("td", "th"):
            denominator = max(len(first.content), len(second.content))
            return Levenshtein.distance(first.content, second.content) / denominator if denominator else 0.0
        return 0.0


def cell_tokens(element):
    tokens = list(element.text or "")
    for child in element:
        tokens += [f"<{child.tag}>", *cell_tokens(child), f"</{child.tag}>"]
        tokens += list(child.tail or "")
    return tuple(tokens)


def table_tree(markup, structure_only=False):
    if len(markup) > 2_000_000:
        raise ValueError("Table HTML exceeds 2 MB")
    parser = html.HTMLParser(remove_comments=True, no_network=True, recover=False)
    root = html.fromstring(markup, parser=parser)
    tables = [root] if root.tag == "table" else root.xpath(".//table")
    if len(tables) != 1 or tables[0].xpath(".//table"):
        raise ValueError("Each table output must contain exactly one non-nested table")
    table = tables[0]
    if len(table.xpath(".//*")) > 3000:
        raise ValueError("Table exceeds 3000 nodes")

    def convert(node):
        cell = node.tag in ("td", "th")
        if node.tag not in ("table", "thead", "tbody", "tfoot", "tr", "td", "th"):
            raise ValueError(f"Unsupported table element: {node.tag}")
        rowspan, colspan = int(node.get("rowspan", "1")), int(node.get("colspan", "1"))
        if not 1 <= rowspan <= 10000 or not 1 <= colspan <= 10000:
            raise ValueError("Invalid table span")
        return TableNode(node.tag, rowspan, colspan,
                         () if structure_only or not cell else cell_tokens(node),
                         [] if cell else [convert(child) for child in node])

    return convert(table)


def teds(reference, prediction, structure_only=False):
    # PubTabNet-style cell-aware tree edit distance. Explicit extension: <th>
    # cell content and spans are scored just like <td>; tag identity is retained.
    ref = table_tree(reference, structure_only)
    if not prediction.strip():
        return 0.0
    try:
        pred = table_tree(prediction, structure_only)
    except (ValueError, etree.ParserError, etree.XMLSyntaxError):
        return 0.0

    def size(node):
        return 1 + sum(size(child) for child in node.children)

    # Match PubTabNet's denominator: descendants of the table root, not root.
    denominator = max(size(ref), size(pred)) - 1
    distance = APTED(ref, pred, TableConfig()).compute_edit_distance()
    return max(0.0, 1 - distance / max(1, denominator))


def normalize_field(value, kind="text"):
    if value is None:
        return None
    text = normalize_text(value)
    if not text:
        return None
    if kind == "date":
        for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, pattern).date().isoformat()
            except ValueError:
                pass
    elif kind == "amount":
        number = re.sub(r"(?i)(PLN|zł|EUR|USD)", "", text).strip().replace(" ", "")
        if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+,\d{1,2}", number):
            number = number.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+\.\d{1,2}", number):
            number = number.replace(",", "")
        elif "," in number and "." not in number:
            number = number.replace(",", ".")
        try:
            amount = Decimal(number)
            if amount.is_finite():
                return format(amount.normalize(), "f")
        except InvalidOperation:
            pass
    elif kind == "identifier":
        return re.sub(r"[\s-]", "", text).upper()
    elif kind == "address":
        return re.sub(r"[.,]", "", text.casefold())
    return text


def kie_counts(reference, prediction, field_types):
    expected = {(key, normalize_field(value, field_types.get(key, "text"))) for key, value in reference.items()}
    actual = {(key, normalize_field(value, field_types.get(key, "text"))) for key, value in prediction.items()}
    expected = {item for item in expected if item[1] is not None}
    actual = {item for item in actual if item[1] is not None}
    return {"tp": len(expected & actual), "fp": len(actual - expected), "fn": len(expected - actual)}
