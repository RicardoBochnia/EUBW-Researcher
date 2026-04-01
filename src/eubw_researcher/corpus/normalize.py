from __future__ import annotations

import logging
import re
import zlib
from io import BytesIO
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple
from xml.etree import ElementTree

from pypdf import PdfReader

PDF_LOGGER = logging.getLogger("pypdf")


def _heading_level_for_class(class_name: str) -> Optional[int]:
    tokens = {token.strip().lower() for token in class_name.split() if token.strip()}
    if "oj-hd-ti" in tokens or "oj-doc-ti" in tokens:
        return 1
    if "oj-ti-part" in tokens or "oj-ti-chap" in tokens or "oj-ti-annex" in tokens:
        return 2
    if "oj-ti-section-1" in tokens:
        return 2
    if "oj-ti-section-2" in tokens:
        return 3
    if "oj-ti-section-3" in tokens:
        return 4
    if "oj-ti-art" in tokens:
        return 3
    return None


def _looks_like_html_document(raw_text: str) -> bool:
    sample = raw_text[:4000].lower()
    return any(
        token in sample
        for token in ["<html", "<body", "<div", "<p", "<table", "<h1", "<h2", "<article", "<section"]
    )


class _HTMLToTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self._title: Optional[str] = None
        self._in_title = False
        self._head_depth = 0
        self._ignored_stack: List[str] = []

    @property
    def title(self) -> Optional[str]:
        return self._title.strip() if self._title else None

    def _should_ignore_tag(self, tag: str, attrs_dict: dict) -> bool:
        if tag in {"style", "script", "svg", "noscript"}:
            return True
        if tag == "nav":
            return True
        combined = " ".join(
            [attrs_dict.get("class", ""), attrs_dict.get("id", ""), attrs_dict.get("role", "")]
        ).lower()
        return "toc" in combined or "table-of-contents" in combined

    def _push_heading(self, level: int) -> None:
        clamped_level = max(1, min(level, 6))
        self.parts.append(f"\n{'#' * clamped_level} ")

    def _append_text(self, text: str) -> None:
        normalized = re.sub(r"\s+", " ", unescape(text).replace("\xa0", " ")).strip()
        if not normalized or normalized in {"¶", "▲"}:
            return
        if self.parts and not str(self.parts[-1]).endswith((" ", "\n", "# ")):
            self.parts.append(" ")
        self.parts.append(normalized)

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        if tag == "head":
            self._head_depth += 1
            return
        if self._ignored_stack or self._should_ignore_tag(tag, attrs_dict):
            self._ignored_stack.append(tag)
            return

        class_name = attrs_dict.get("class", "")

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._push_heading(int(tag[1]))
        elif tag == "p":
            heading_level = _heading_level_for_class(class_name)
            if heading_level is not None:
                self._push_heading(heading_level)
            else:
                self.parts.append("\n")
        elif tag in {"div", "section", "article", "tr", "table"}:
            self.parts.append("\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "head":
            self._head_depth = max(0, self._head_depth - 1)
            return
        if self._ignored_stack:
            self._ignored_stack.pop()
            return
        if tag == "title":
            self._in_title = False
        elif tag in {"p", "div", "section", "article", "table", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title = (self._title or "") + unescape(data)
            return
        if self._head_depth > 0 or self._ignored_stack:
            return
        self._append_text(data)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1].lower()
    return tag.lower()


def _normalize_xml_text(raw_text: str) -> Tuple[str, Optional[str]]:
    root = ElementTree.fromstring(raw_text)
    parts: List[str] = []
    title: Optional[str] = None
    heading_tags = {"title", "head", "section", "chapter", "annex", "article", "part"}
    paragraph_tags = {"p", "para", "paragraph", "li", "item", "text", "cell"}

    def append_text(value: Optional[str]) -> None:
        if value is None:
            return
        normalized = re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
        if not normalized:
            return
        parts.append(normalized)

    def walk(node, depth: int = 1) -> None:
        nonlocal title
        name = _local_name(node.tag)
        text = (node.text or "").strip()
        if name in heading_tags and text:
            normalized_heading = re.sub(r"\s+", " ", text)
            if title is None and name == "title":
                title = normalized_heading
            parts.append(f"\n{'#' * max(1, min(depth, 6))} {normalized_heading}")
        elif name in paragraph_tags and text:
            parts.append("\n")
            append_text(text)
        elif text and depth == 1 and title is None:
            title = re.sub(r"\s+", " ", text)
            parts.append(f"\n# {title}")

        for child in list(node):
            walk(child, depth + 1 if name in heading_tags else depth)
            if child.tail:
                append_text(child.tail)

    walk(root)
    body = "\n".join(part for part in parts if part).strip()
    if not body:
        raise ValueError("XML normalization produced no usable text.")
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body, title


def _pdf_literal_to_text(raw_bytes: bytes) -> str:
    text = raw_bytes.decode("latin-1", errors="ignore")
    extracted: List[str] = []
    for value in re.findall(r"\((.*?)\)\s*Tj", text, re.DOTALL):
        extracted.append(value)
    for array in re.findall(r"\[(.*?)\]\s*TJ", text, re.DOTALL):
        extracted.extend(re.findall(r"\((.*?)\)", array, re.DOTALL))
    joined = "\n".join(
        re.sub(r"\s+", " ", item.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")).strip()
        for item in extracted
        if item.strip()
    )
    return joined.strip()


def _extract_pdf_text(raw_bytes: bytes) -> str:
    previous_level = PDF_LOGGER.level
    try:
        PDF_LOGGER.setLevel(logging.ERROR)
        reader = PdfReader(BytesIO(raw_bytes), strict=False)
        page_texts = [
            re.sub(r"\s+", " ", page.extract_text() or "").strip()
            for page in reader.pages
        ]
        extracted = "\n".join(text for text in page_texts if text).strip()
        if extracted:
            return extracted
    except Exception:
        pass
    finally:
        PDF_LOGGER.setLevel(previous_level)

    stream_matches = list(
        re.finditer(rb"(<<.*?>>)?\s*stream\r?\n(.*?)\r?\nendstream", raw_bytes, re.DOTALL)
    )
    extracted_chunks: List[str] = []
    for match in stream_matches:
        stream_dict = match.group(1) or b""
        stream_bytes = match.group(2)
        if b"/FlateDecode" in stream_dict:
            try:
                stream_bytes = zlib.decompress(stream_bytes)
            except zlib.error:
                continue
        text = _pdf_literal_to_text(stream_bytes)
        if text:
            extracted_chunks.append(text)

    if not extracted_chunks:
        fallback = _pdf_literal_to_text(raw_bytes)
        if fallback:
            extracted_chunks.append(fallback)

    if not extracted_chunks:
        raise ValueError("PDF normalization produced no extractable text.")

    combined = "\n".join(chunk for chunk in extracted_chunks if chunk).strip()
    if not combined:
        raise ValueError("PDF normalization produced empty text.")
    return combined


def normalize_text_content(raw_text: str, source_format: str) -> Tuple[str, Optional[str]]:
    normalized_format = source_format.lower()
    if (
        "html" in normalized_format
        or "xhtml" in normalized_format
        or normalized_format.endswith((".html", ".htm", ".xhtml"))
        or ("xml" in normalized_format and _looks_like_html_document(raw_text))
    ):
        parser = _HTMLToTextParser()
        parser.feed(raw_text)
        body = "".join(parser.parts)
        body = re.sub(r"[ \t]+\n", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        return body.strip(), parser.title
    if "xml" in normalized_format or normalized_format.endswith(".xml"):
        return _normalize_xml_text(raw_text)
    return raw_text.strip(), None


def normalize_bytes_content(
    raw_bytes: bytes,
    source_format: str,
) -> Tuple[str, Optional[str], str, Optional[str]]:
    normalized_format = source_format.lower()
    if "pdf" in normalized_format or normalized_format.endswith(".pdf"):
        return (
            _extract_pdf_text(raw_bytes),
            None,
            "pdf",
            "Extracted text from PDF using pypdf with stream fallback.",
        )

    raw_text = raw_bytes.decode("utf-8", errors="replace")
    normalized_text, title = normalize_text_content(raw_text, source_format)
    output_format = (
        "xml"
        if "xml" in normalized_format or normalized_format.endswith(".xml")
        else "html"
        if any(token in normalized_format for token in ["html", "xhtml", ".htm"])
        else "markdown"
        if any(token in normalized_format for token in [".md", "markdown"])
        else normalized_format.lstrip(".") or "text"
    )
    note = (
        "Normalized HTML-like source."
        if output_format == "html"
        else "Normalized XML source."
        if output_format == "xml"
        else "Read text source."
    )
    if not normalized_text.strip():
        raise ValueError(f"{output_format.upper()} normalization produced no usable text.")
    return normalized_text, title, output_format, note


def normalize_local_source(path: Path) -> Tuple[str, Optional[str], str, Optional[str]]:
    return normalize_bytes_content(path.read_bytes(), path.suffix.lower())


def read_local_source_text(path: Path) -> str:
    normalized_text, _, _, _ = normalize_local_source(path)
    return normalized_text
