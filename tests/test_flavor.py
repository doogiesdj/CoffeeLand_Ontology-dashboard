"""Phase 2 (flavor layer) — provenance, completeness and pipeline tests."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import OWL, RDF, RDFS, Graph, Namespace

ROOT = Path(__file__).resolve().parent.parent
FLAVOR_TTL = ROOT / "data" / "coffeeland_flavor.ttl"
COF = Namespace("http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#")

_spec = importlib.util.spec_from_file_location("build_flavor_ttl", ROOT / "scripts" / "build_flavor_ttl.py")
bf = importlib.util.module_from_spec(_spec)
sys.modules["build_flavor_ttl"] = bf  # dataclasses resolve their module via sys.modules
_spec.loader.exec_module(bf)


@pytest.fixture(scope="module")
def html() -> str:
    return (ROOT / "dashboard.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def profiles(html: str) -> dict[str, "bf.Profile"]:
    return {p.subject: p for p in bf.build_profiles(html, bf.load_rdf())}


@pytest.fixture(scope="module")
def ttl() -> Graph:
    assert FLAVOR_TTL.exists(), "run: python scripts/build_flavor_ttl.py"
    g = Graph()
    g.parse(FLAVOR_TTL, format="turtle")
    return g


def notes_of(g: Graph, subject: str) -> set[str]:
    return {str(o).split("#")[-1] for o in g.objects(COF[subject], COF.hasFlavorNote)}


# ── Completeness: nothing in the sources is silently dropped or invented ──

def test_every_source_fragment_is_classified(html: str) -> None:
    countries = bf.js_object_flavors(html, "COUNTRY_DATA")
    harvests = bf.js_object_flavors(html, "HARVEST_DATA")
    frags = [f for raw in countries.values() for f in bf.country_fragments(raw)]
    frags += [f for raw in harvests.values() for f in bf.harvest_fragments(raw)]
    assert len(countries) == 23 and len(harvests) == 34
    assert bf.unclassified_fragments(frags) == []


def test_no_dead_fragment_entries(html: str) -> None:
    countries = bf.js_object_flavors(html, "COUNTRY_DATA")
    harvests = bf.js_object_flavors(html, "HARVEST_DATA")
    used = {f for raw in countries.values() for f in bf.country_fragments(raw)}
    used |= {f for raw in harvests.values() for f in bf.harvest_fragments(raw)}
    assert set(bf.FRAGMENT_TAGS) - used == set()


def test_all_tags_are_known() -> None:
    known = set(bf.NOTES) | {f"acidity:{l}" for l in bf.ACIDITY_LEVELS} | {f"body:{l}" for l in bf.BODY_LEVELS}
    for frag, tags in bf.FRAGMENT_TAGS.items():
        assert set(tags) <= known, frag
    for subject, pairs in bf.COMMENT_TAGS.items():
        assert {t for t, _ in pairs} <= known, subject


def test_note_categories_are_flavor_wheel_categories() -> None:
    for note_id, (cat, ko, en) in bf.NOTES.items():
        assert cat in bf.CATEGORIES, note_id
        assert ko and en


def test_comment_evidence_appears_in_comment() -> None:
    g = bf.load_rdf()
    for subject, pairs in bf.COMMENT_TAGS.items():
        comment = str(g.value(COF[subject], RDFS.comment))
        for _, snippet in pairs:
            assert snippet in comment, (subject, snippet)


def test_committed_ttl_is_up_to_date() -> None:
    assert FLAVOR_TTL.read_text(encoding="utf-8") == bf.build()


# ── Spot checks against the source text (hand-written expectations) ──

def test_ethiopia_country_profile(ttl: Graph) -> None:
    # COUNTRY_DATA Ethiopia: 블루베리, 재스민, 장미, 와인, 복숭아, 열대과일
    assert notes_of(ttl, "Ethiopia") == {
        "FN_Blueberry", "FN_Jasmine", "FN_Rose", "FN_Winey", "FN_Peach", "FN_TropicalFruit"}


def test_sumatra_harvest_profile(ttl: Graph) -> None:
    # HARVEST_DATA Sumatra: Earthy, cedar, dark chocolate, tobacco, full body, low acidity
    assert notes_of(ttl, "Harvest_Sumatra_2023") == {
        "FN_Earthy", "FN_Woody", "FN_DarkChocolate", "FN_Tobacco"}
    assert str(ttl.value(COF.Harvest_Sumatra_2023, COF.hasBodyLevel)) == "Full"
    assert str(ttl.value(COF.Harvest_Sumatra_2023, COF.hasAcidityLevel)) == "Low"


def test_multi_year_harvests_share_region_profile(ttl: Graph) -> None:
    assert notes_of(ttl, "Harvest_Narino_2023") == notes_of(ttl, "Harvest_Narino_2024") != set()
    assert notes_of(ttl, "Harvest_Nyeri_2023") == notes_of(ttl, "Harvest_Nyeri_2024") != set()


def test_processing_and_roast_profiles(ttl: Graph) -> None:
    assert str(ttl.value(COF.Washed_Process, COF.hasAcidityLevel)) == "High"
    assert notes_of(ttl, "Natural_Process") == {"FN_Fruity"}
    assert str(ttl.value(COF.Natural_Process, COF.hasBodyLevel)) == "Full"
    assert notes_of(ttl, "Dark_Roast") == {"FN_Smoky", "FN_Caramel"}
    assert str(ttl.value(COF.Espresso_Roast, COF.hasAcidityLevel)) == "Low"


def test_ignored_only_fragments_produce_nothing(ttl: Graph) -> None:
    # "응축된 풍미(Peaberry)" and "독특한 몬순 캐릭터" are descriptive, not notes
    assert all(not bf.FRAGMENT_TAGS[f] for f in ["응축된 풍미(Peaberry)", "독특한 몬순 캐릭터", "clean finish"])


def test_profiles_cover_expected_subjects(profiles: dict) -> None:
    assert sum(1 for s in profiles if s.startswith("Harvest_")) == 36   # 34 regions, 2 with two years
    assert {"Ethiopia", "Kenya", "Brazil", "Washed_Process", "Dark_Roast", "QG_Guatemala_SHB"} <= set(profiles)


def test_schema(ttl: Graph) -> None:
    assert (COF.FlavorNote, RDFS.subClassOf, COF.QualityAndProcessing) in ttl
    assert (COF.hasFlavorNote, RDF.type, OWL.ObjectProperty) in ttl
    assert len(set(ttl.subjects(RDF.type, COF.FlavorNote))) == len(bf.NOTES)
    for level in ttl.objects(None, COF.hasAcidityLevel):
        assert str(level) in bf.ACIDITY_LEVELS
    for level in ttl.objects(None, COF.hasBodyLevel):
        assert str(level) in bf.BODY_LEVELS


# ── Pipeline ──

@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("docs")
    env = {**os.environ, "COFFEELAND_OUT_DIR": str(out), "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "rdf_to_json.py")],
                   check=True, env=env, capture_output=True)
    return json.loads((out / "ontology_data.json").read_text(encoding="utf-8"))


def test_converter_exports_flavor(converted: dict) -> None:
    qp = next(n for n in converted["classHierarchy"] if n["name"] == "QualityAndProcessing")
    fn = next(c for c in qp["children"] if c["name"] == "FlavorNote")
    assert fn["instanceCount"] == len(bf.NOTES)
    eth = converted["instanceDetails"]["Ethiopia"]["properties"]
    assert set(eth["hasFlavorNote"]["values"]) >= {"FN_Jasmine", "FN_Blueberry"}
    assert converted["instanceDetails"]["FN_Jasmine"]["properties"]["hasFlavorCategory"]["value"] == "Floral"
    assert converted["instanceDetails"]["Washed_Process"]["properties"]["hasAcidityLevel"]["value"] == "High"


def test_converter_exports_korean_labels(converted: dict) -> None:
    assert converted["instanceDetails"]["FN_Jasmine"]["label"] == "재스민"
    assert converted["instanceDetails"]["BM_PourOver"]["label"] == "푸어오버"


def test_converter_keeps_all_notes_per_subject(converted: dict) -> None:
    """instanceDetails truncates object values to 10 — profiles must fit."""
    for name, detail in converted["instanceDetails"].items():
        vals = detail["properties"].get("hasFlavorNote", {}).get("values", [])
        assert len(vals) <= 10, name
