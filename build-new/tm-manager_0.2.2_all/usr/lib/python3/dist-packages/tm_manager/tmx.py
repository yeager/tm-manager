"""TMX file handling - parse, create, merge, search."""

import xml.etree.ElementTree as ET
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path


class TranslationUnit:
    """A single translation unit (segment)."""

    def __init__(self, source="", target="", source_lang="en", target_lang="",
                 created=None, project="", note=""):
        self.source = source
        self.target = target
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.created = created or datetime.now().isoformat()
        self.project = project
        self.note = note

    def to_dict(self):
        return {
            "source": self.source,
            "target": self.target,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "created": self.created,
            "project": self.project,
            "note": self.note,
        }


class TMXFile:
    """Represents a TMX file with translation units."""

    def __init__(self, path=None):
        self.path = path
        self.units = []
        self.source_lang = "en"
        self.modified = False
        if path and Path(path).exists():
            self.load(path)

    def load(self, path):
        """Load a TMX file."""
        self.path = str(path)
        self.units = []
        tree = ET.parse(path)
        root = tree.getroot()

        header = root.find("header")
        if header is not None:
            self.source_lang = header.get("srclang", "en")

        body = root.find("body")
        if body is None:
            return

        for tu_elem in body.findall("tu"):
            project = tu_elem.get("tuid", "")
            created = tu_elem.get("creationdate", "")
            note_elem = tu_elem.find("note")
            note = note_elem.text if note_elem is not None else ""

            segments = {}
            for tuv in tu_elem.findall("tuv"):
                lang = tuv.get("{http://www.w3.org/XML/1998/namespace}lang", tuv.get("lang", ""))
                seg = tuv.find("seg")
                if seg is not None and seg.text:
                    segments[lang] = seg.text

            if len(segments) >= 2:
                langs = list(segments.keys())
                src_lang = self.source_lang if self.source_lang in langs else langs[0]
                for lang in langs:
                    if lang != src_lang:
                        tu = TranslationUnit(
                            source=segments.get(src_lang, ""),
                            target=segments.get(lang, ""),
                            source_lang=src_lang,
                            target_lang=lang,
                            created=created,
                            project=project,
                            note=note,
                        )
                        self.units.append(tu)
            elif len(segments) == 1:
                lang, text = list(segments.items())[0]
                tu = TranslationUnit(
                    source=text, target="", source_lang=lang, target_lang="",
                    created=created, project=project, note=note,
                )
                self.units.append(tu)

        self.modified = False

    def save(self, path=None):
        """Save to TMX format."""
        path = path or self.path
        if not path:
            raise ValueError("No path specified")

        root = ET.Element("tmx", version="1.4")
        header = ET.SubElement(root, "header",
                               creationtool="tm-manager",
                               creationtoolversion="0.1.0",
                               segtype="sentence",
                               adminlang="en",
                               srclang=self.source_lang,
                               datatype="plaintext")
        body = ET.SubElement(root, "body")

        for unit in self.units:
            tu_elem = ET.SubElement(body, "tu")
            if unit.project:
                tu_elem.set("tuid", unit.project)
            if unit.created:
                tu_elem.set("creationdate", unit.created)
            if unit.note:
                note_elem = ET.SubElement(tu_elem, "note")
                note_elem.text = unit.note

            tuv_src = ET.SubElement(tu_elem, "tuv")
            tuv_src.set("xml:lang", unit.source_lang)
            seg_src = ET.SubElement(tuv_src, "seg")
            seg_src.text = unit.source

            if unit.target and unit.target_lang:
                tuv_tgt = ET.SubElement(tu_elem, "tuv")
                tuv_tgt.set("xml:lang", unit.target_lang)
                seg_tgt = ET.SubElement(tuv_tgt, "seg")
                seg_tgt.text = unit.target

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="unicode", xml_declaration=True)
        self.path = path
        self.modified = False

    def search(self, query, threshold=0.6):
        """Fuzzy search in translation units."""
        results = []
        query_lower = query.lower()
        for unit in self.units:
            src_ratio = SequenceMatcher(None, query_lower, unit.source.lower()).ratio()
            tgt_ratio = SequenceMatcher(None, query_lower, unit.target.lower()).ratio()
            score = max(src_ratio, tgt_ratio)
            if score >= threshold:
                results.append((unit, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def filter_units(self, source_lang=None, target_lang=None, project=None,
                     date_from=None, date_to=None):
        """Filter units by criteria."""
        results = self.units
        if source_lang:
            results = [u for u in results if u.source_lang == source_lang]
        if target_lang:
            results = [u for u in results if u.target_lang == target_lang]
        if project:
            results = [u for u in results if project.lower() in u.project.lower()]
        if date_from:
            results = [u for u in results if u.created >= date_from]
        if date_to:
            results = [u for u in results if u.created <= date_to]
        return results

    def get_languages(self):
        """Get all language pairs."""
        langs = set()
        for u in self.units:
            if u.source_lang:
                langs.add(u.source_lang)
            if u.target_lang:
                langs.add(u.target_lang)
        return sorted(langs)

    def get_language_pairs(self):
        """Get unique language pairs."""
        pairs = set()
        for u in self.units:
            if u.source_lang and u.target_lang:
                pairs.add((u.source_lang, u.target_lang))
        return sorted(pairs)

    def get_stats(self):
        """Get statistics about the TMX file."""
        return {
            "total_segments": len(self.units),
            "languages": self.get_languages(),
            "language_pairs": self.get_language_pairs(),
            "projects": sorted(set(u.project for u in self.units if u.project)),
        }

    def merge(self, other):
        """Merge another TMXFile into this one, avoiding duplicates."""
        existing = set()
        for u in self.units:
            existing.add((u.source, u.target, u.source_lang, u.target_lang))
        added = 0
        for u in other.units:
            key = (u.source, u.target, u.source_lang, u.target_lang)
            if key not in existing:
                self.units.append(u)
                existing.add(key)
                added += 1
        if added > 0:
            self.modified = True
        return added

    def add_unit(self, unit):
        self.units.append(unit)
        self.modified = True

    def remove_unit(self, index):
        if 0 <= index < len(self.units):
            self.units.pop(index)
            self.modified = True


def import_po(path, source_lang="en", target_lang=""):
    """Import a .po file into translation units."""
    units = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple PO parser
    import re
    entries = re.split(r'\n(?=msgid )', content)
    for entry in entries:
        msgid_match = re.search(r'msgid "(.*?)"', entry, re.DOTALL)
        msgstr_match = re.search(r'msgstr "(.*?)"', entry, re.DOTALL)
        if msgid_match and msgstr_match:
            msgid = msgid_match.group(1)
            msgstr = msgstr_match.group(1)
            if msgid and msgstr:
                # Handle multi-line
                msgid = msgid.replace('"\n"', '')
                msgstr = msgstr.replace('"\n"', '')
                units.append(TranslationUnit(
                    source=msgid, target=msgstr,
                    source_lang=source_lang, target_lang=target_lang,
                ))
    return units


def import_xliff(path):
    """Import an XLIFF file into translation units."""
    units = []
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"xliff": "urn:oasis:names:tc:xliff:document:1.2"}

    for file_elem in root.findall(".//xliff:file", ns) or root.findall(".//file"):
        source_lang = file_elem.get("source-language", "en")
        target_lang = file_elem.get("target-language", "")

        for tu in file_elem.findall(".//xliff:trans-unit", ns) or file_elem.findall(".//trans-unit"):
            source = tu.find("xliff:source", ns)
            if source is None:
                source = tu.find("source")
            target = tu.find("xliff:target", ns)
            if target is None:
                target = tu.find("target")

            if source is not None and source.text:
                units.append(TranslationUnit(
                    source=source.text,
                    target=target.text if target is not None and target.text else "",
                    source_lang=source_lang,
                    target_lang=target_lang,
                ))

    # Try without namespace if nothing found
    if not units:
        for file_elem in root.iter("file"):
            source_lang = file_elem.get("source-language", "en")
            target_lang = file_elem.get("target-language", "")
            for tu in file_elem.iter("trans-unit"):
                source = tu.find("source")
                target = tu.find("target")
                if source is not None and source.text:
                    units.append(TranslationUnit(
                        source=source.text,
                        target=target.text if target is not None and target.text else "",
                        source_lang=source_lang,
                        target_lang=target_lang,
                    ))
    return units


def import_ts(path):
    """Import a Qt .ts file into translation units."""
    units = []
    tree = ET.parse(path)
    root = tree.getroot()
    target_lang = root.get("language", "")

    for context in root.findall("context"):
        for message in context.findall("message"):
            source = message.find("source")
            translation = message.find("translation")
            if source is not None and source.text:
                t_text = ""
                if translation is not None and translation.text:
                    t_type = translation.get("type", "")
                    if t_type != "unfinished":
                        t_text = translation.text
                units.append(TranslationUnit(
                    source=source.text,
                    target=t_text,
                    source_lang="en",
                    target_lang=target_lang,
                ))
    return units


def export_po(units, path, target_lang=""):
    """Export translation units to PO format."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'# Translation Memory Export\n')
        f.write(f'msgid ""\nmsgstr ""\n')
        f.write(f'"Content-Type: text/plain; charset=UTF-8\\n"\n')
        if target_lang:
            f.write(f'"Language: {target_lang}\\n"\n')
        f.write(f'\n')
        for unit in units:
            source = unit.source.replace('"', '\\"')
            target = unit.target.replace('"', '\\"')
            f.write(f'msgid "{source}"\n')
            f.write(f'msgstr "{target}"\n\n')
