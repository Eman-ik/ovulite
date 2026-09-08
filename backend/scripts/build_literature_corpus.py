"""Build a reproducible, license-filtered bovine reproduction corpus from Europe PMC.

Stores licensed article text and attribution, never manufactures ET observations.
Run from backend: python scripts/build_literature_corpus.py
"""
import hashlib
import html
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
DEST = Path(__file__).resolve().parents[1] / "resources" / "literature_seed"
QUERY = '(TITLE_ABS:bovine OR TITLE_ABS:cattle) AND (TITLE_ABS:"embryo transfer" OR TITLE_ABS:"in vitro fertilization" OR TITLE_ABS:"in vitro embryo") AND OPEN_ACCESS:y AND FIRST_PDATE:[1900-01-01 TO 2026-09-08]'


def clean(markup):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(markup or ""))).strip()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "OvuliteAcademicCorpus/1.0"
    response = session.get(f"{BASE}/search", params={"query": QUERY, "format": "json", "resultType": "core", "pageSize": 250}, timeout=45)
    response.raise_for_status()
    records = response.json()["resultList"]["result"]
    documents, rejected = [], []
    for record in records:
        pmcid = record.get("pmcid")
        title = clean(record.get("title"))
        abstract = clean(record.get("abstractText"))
        if not pmcid or len(abstract) < 200:
            continue
        if re.search(r"\b(ovine|porcine|pig|pigs|human|small ruminants|sheep|goat|mouse|mice)\b", title.lower()):
            continue
        if any(word in str(record.get("pubTypeList", "")).lower() for word in ("preprint", "retraction", "retracted")):
            continue
        if not re.search(r"embryo|oocyt|recipient|progesterone|lute|pregnan|cryopreserv|synchron|fertiliz|heat stress|in vitro", title.lower()):
            continue
        # Require cattle/bovine in the title or abstract plus an explicit IVF/ET phrase.
        content = (title + " " + abstract).lower()
        if not re.search(r"\b(bovine|cattle)\b", content) or not any(term in content for term in ("embryo transfer", "in vitro fertilization", "in vitro embryo", "in-vitro fertilization", "in-vitro embryo")):
            continue
        cache = DEST / "license_xml" / f"{pmcid}.xml"
        cache.parent.mkdir(parents=True, exist_ok=True)
        old_cache = Path(__file__).resolve().parents[1] / "data" / "literature_seed" / f"{pmcid}.xml"
        try:
            if cache.exists():
                xml = cache.read_bytes()
            elif old_cache.exists():
                xml = old_cache.read_bytes()
            else:
                response = session.get(f"{BASE}/{pmcid}/fullTextXML", timeout=35)
                response.raise_for_status()
                xml = response.content
            root = ET.fromstring(xml)
            licenses = root.findall(".//article-meta/permissions/license")
            license_urls = [value for node in licenses for key, value in node.attrib.items() if key.endswith("href")]
            license_urls += [value for node in licenses for descendant in node.iter() for key, value in descendant.attrib.items() if key.endswith("href")]
            reusable = next((url for url in license_urls if re.search(r"creativecommons.org/(licenses/by/|publicdomain/zero/)", url)), None)
            if not reusable:
                rejected.append({"pmcid": pmcid, "reason": "No explicit CC BY or CC0 license URL", "licenses": license_urls})
                continue
            # Retain licensed abstract and article body, excluding the reference list.
            xml_abstract = root.find(".//article-meta/abstract")
            if xml_abstract is not None:
                abstract = " ".join(" ".join(xml_abstract.itertext()).split())
            body = root.find(".//body")
            if body is not None:
                for parent in body.iter():
                    for child in list(parent):
                        if child.tag in {"ref-list", "ref"}:
                            parent.remove(child)
            body_text = " ".join(" ".join(body.itertext()).split()) if body is not None else ""
            full_text = (abstract + "\n\n" + body_text).strip()
            source_text = full_text[:180000]
            cache.write_bytes(xml)
            topics = [term for term in ("progesterone", "recipient", "cryopreservation", "heat stress", "synchronization", "blastocyst", "embryo transfer") if term in content]
            documents.append({"title": title, "authors": clean(record.get("authorString", "")), "year": int(record["pubYear"]),
                "source_url": f"https://europepmc.org/articles/{pmcid}", "source_kind": "peer_reviewed",
                "rights": f"{reusable} — attribution retained; whitespace normalized; references excluded",
                "content": source_text, "pmcid": pmcid, "doi": record.get("doi"), "topics": topics,
                "content_scope": "abstract_and_body" if body_text else "abstract", "truncated": len(full_text) > 180000, "license_url": reusable,
                "checksum": hashlib.sha256(source_text.encode()).hexdigest()})
            print(f"Accepted {len(documents)}: {pmcid} {title[:90]}", flush=True)
            if len(documents) >= 60:
                break
            time.sleep(0.15)
        except (requests.RequestException, ET.ParseError, ValueError) as error:
            rejected.append({"pmcid": pmcid, "reason": str(error)})
    manifest = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "query": QUERY,
        "source": BASE, "selection": "Bovine/cattle IVF/ET topic filter; explicit CC BY or CC0 XML license; abstract available. Screening does not imply a formal quality appraisal.",
        "documents": documents, "excluded": rejected}
    (DEST / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(documents)} licensed papers to {DEST / 'manifest.json'}", flush=True)
    if len(documents) < 50:
        raise SystemExit("Corpus target not reached; inspect exclusions")


if __name__ == "__main__":
    main()
