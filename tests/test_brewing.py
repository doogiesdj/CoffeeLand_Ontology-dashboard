"""Phase 1 (brewing knowledge) — data provenance and pipeline tests.

Every brew parameter in data/coffeeland_brewing.ttl must be backed by an
evidence snippet that appears verbatim in that recipe's hasInstructions
text in the main RDF. Nothing is allowed in the TTL that isn't listed here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef

ROOT = Path(__file__).resolve().parent.parent
MAIN_RDF = ROOT / "data" / "coffeeland_final_v4.rdf"
BREWING_TTL = ROOT / "data" / "coffeeland_brewing.ttl"
COF = Namespace("http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#")

# (property, min, max) → evidence snippets that must appear in hasInstructions.
# max=None for single-valued properties; strings for categorical values.
# "note" marks values derived from (not literally stated in) the text.
EVIDENCE: dict[str, list[dict]] = {
    "Recipe_ClassicEspresso": [
        {"prop": "hasDoseGrams", "min": 18, "max": 18, "ev": ["원두 18g"]},
        {"prop": "hasYieldMl", "min": 36, "max": 36, "ev": ["더블샷 36ml"]},
        {"prop": "hasWaterTempC", "min": 92, "max": 94, "ev": ["92-94°C"]},
        {"prop": "hasPressureBar", "min": 9, "ev": ["9bar"]},
        {"prop": "hasBrewTimeSec", "min": 25, "max": 30, "ev": ["25-30초간"]},
        {"prop": "hasGrindSize", "min": "Fine", "ev": ["곱게 분쇄"]},
        {"prop": "hasEspressoShots", "min": 2, "ev": ["더블샷"]},
    ],
    "Recipe_Doppio": [
        {"prop": "hasDoseGrams", "min": 18, "max": 20, "ev": ["원두 18-20g"]},
        {"prop": "hasYieldMl", "min": 60, "max": 70, "ev": ["60-70ml"]},
        {"prop": "hasBrewTimeSec", "min": 25, "max": 30, "ev": ["25-30초간"]},
        {"prop": "hasEspressoShots", "min": 2, "ev": ["더블 바스켓"]},
    ],
    "Recipe_Ristretto": [
        {"prop": "hasDoseGrams", "min": 18, "max": 18, "ev": ["원두량(18g)"]},
        {"prop": "hasYieldMl", "min": 15, "max": 20, "ev": ["15-20ml"]},
        {"prop": "hasBrewTimeSec", "min": 25, "max": 30, "ev": ["(25-30초)"]},
    ],
    "Recipe_Lungo": [
        {"prop": "hasDoseGrams", "min": 18, "max": 18, "ev": ["원두 18g"]},
        {"prop": "hasYieldMl", "min": 50, "max": 60, "ev": ["50-60ml"]},
        {"prop": "hasBrewTimeSec", "min": 40, "max": None, "ev": ["40초 이상"]},
    ],
    "Recipe_Americano": [
        {"prop": "hasYieldMl", "min": 60, "max": 60, "ev": ["더블 에스프레소(60ml)"]},
        {"prop": "hasEspressoShots", "min": 2, "ev": ["더블 에스프레소"]},
    ],
    "Recipe_FlatWhite": [
        {"prop": "hasYieldMl", "min": 40, "max": 40, "ev": ["약 40ml"]},
        {"prop": "hasEspressoShots", "min": 2, "ev": ["리스트레토 더블샷"]},
    ],
    "Recipe_CaffeLatte": [{"prop": "hasEspressoShots", "min": 1, "ev": ["싱글 에스프레소"]}],
    "Recipe_Macchiato": [{"prop": "hasEspressoShots", "min": 1, "ev": ["싱글 에스프레소"]}],
    "Recipe_CaramelMacchiato": [{"prop": "hasEspressoShots", "min": 2, "ev": ["에스프레소 더블샷"]}],
    "Recipe_Cortado": [{"prop": "hasEspressoShots", "min": 2, "ev": ["에스프레소 더블샷"]}],
    "Recipe_Mocha": [{"prop": "hasEspressoShots", "min": 1, "ev": ["에스프레소 싱글샷"]}],
    "Recipe_Affogato": [{"prop": "hasEspressoShots", "min": 1, "ev": ["에스프레소 싱글샷"]}],
    "Recipe_IcedAmericano": [{"prop": "hasEspressoShots", "min": 2, "ev": ["더블 에스프레소"]}],
    "Recipe_Shakerato": [{"prop": "hasEspressoShots", "min": 2, "ev": ["에스프레소 더블샷"]}],
    "Recipe_HoneyLatte": [{"prop": "hasEspressoShots", "min": 1, "ev": ["에스프레소 싱글샷"]}],
    "Recipe_VanillaLatte": [{"prop": "hasEspressoShots", "min": 1, "ev": ["에스프레소 싱글샷"]}],
    "Recipe_ColdBrewConcentrate": [
        {"prop": "hasBrewRatio", "min": "1:8", "ev": ["1:8 비율"]},
        {"prop": "hasBrewTimeSec", "min": 43200, "max": 64800, "ev": ["12-18시간"]},
        {"prop": "hasGrindSize", "min": "Coarse", "ev": ["굵게 분쇄"]},
    ],
    "Recipe_PourOverV60": [
        {"prop": "hasDoseGrams", "min": 20, "max": 20, "ev": ["원두 20g"]},
        {"prop": "hasGrindSize", "min": "Medium", "ev": ["중간 굵기"]},
        {"prop": "hasWaterTempC", "min": 92, "max": 92, "ev": ["92°C"]},
        {"prop": "hasBrewWaterMl", "min": 320, "max": 320, "ev": ["총 320ml"]},
        {"prop": "hasBrewTimeSec", "min": 150, "max": 180, "ev": ["2분30초-3분"]},
    ],
    "Recipe_FrenchPress": [
        {"prop": "hasDoseGrams", "min": 30, "max": 30, "ev": ["원두 30g"]},
        {"prop": "hasGrindSize", "min": "Coarse", "ev": ["굵게 분쇄"]},
        {"prop": "hasWaterTempC", "min": 95, "max": 96, "ev": ["95-96°C"]},
        {"prop": "hasBrewWaterMl", "min": 500, "max": 500, "ev": ["물 500ml"]},
        {"prop": "hasBrewTimeSec", "min": 240, "max": 240, "ev": ["4분간"]},
    ],
    "Recipe_Aeropress": [
        {"prop": "hasDoseGrams", "min": 17, "max": 17, "ev": ["원두 17g"]},
        {"prop": "hasGrindSize", "min": "Fine", "ev": ["곱게 분쇄"]},
        {"prop": "hasWaterTempC", "min": 85, "max": 90, "ev": ["85-90°C"]},
        {"prop": "hasBrewWaterMl", "min": 250, "max": 250, "ev": ["물 250ml"]},
        {"prop": "hasBrewTimeSec", "min": 130, "max": 130,
         "ev": ["10초간 저은 뒤", "1분30초간 우린다", "30초간 천천히 압착"],
         "note": "sequential steps in the text: stir 10s, then steep 90s, then press 30s"},
    ],
    # "5-6분간 가열" is stovetop heating time, not extraction time → not recorded.
    "Recipe_MokaPot": [
        {"prop": "hasGrindSize", "min": "MediumFine", "ev": ["중간-고운 분쇄"]},
    ],
    "Recipe_TurkishCoffee": [
        {"prop": "hasDoseGrams", "min": 7, "max": 7, "ev": ["원두 7g"]},
        {"prop": "hasBrewWaterMl", "min": 80, "max": 80, "ev": ["찬물 80ml"]},
        {"prop": "hasGrindSize", "min": "ExtraFine", "ev": ["밀가루처럼 아주 곱게"]},
    ],
    "Recipe_VietnameseIcedCoffee": [
        {"prop": "hasDoseGrams", "min": 15, "max": 15, "ev": ["원두 15g"]},
        {"prop": "hasGrindSize", "min": "Coarse", "ev": ["굵게 분쇄"]},
        {"prop": "hasBrewTimeSec", "min": 300, "max": 300, "ev": ["5분간 방울방울"]},
    ],
    "Recipe_EthiopianBuna": [{"prop": "hasGrindSize", "min": "Fine", "ev": ["곱게 빻는다"]}],
    "Recipe_MoroccanSpicedCoffee": [
        {"prop": "hasGrindSize", "min": "Fine", "ev": ["곱게 간 원두"]},
        {"prop": "hasBrewTimeSec", "min": 300, "max": 300, "ev": ["5분 정도 우린"]},
    ],
}

# Recipe → BrewMethod, each backed by an evidence snippet.
METHOD_EVIDENCE: dict[str, tuple[str, str]] = {
    "Recipe_ClassicEspresso": ("BM_Espresso", "9bar 압력"),
    "Recipe_Doppio": ("BM_Espresso", "더블 바스켓"),
    "Recipe_Ristretto": ("BM_Espresso", "일반 에스프레소와 동일한"),
    "Recipe_Lungo": ("BM_Espresso", "길게 추출"),
    "Recipe_Americano": ("BM_Espresso", "더블 에스프레소"),
    "Recipe_Cappuccino": ("BM_Espresso", "에스프레소를 추출"),
    "Recipe_FlatWhite": ("BM_Espresso", "리스트레토 더블샷"),
    "Recipe_CaffeLatte": ("BM_Espresso", "싱글 에스프레소"),
    "Recipe_Macchiato": ("BM_Espresso", "싱글 에스프레소"),
    "Recipe_CaramelMacchiato": ("BM_Espresso", "에스프레소 더블샷"),
    "Recipe_Cortado": ("BM_Espresso", "에스프레소 더블샷"),
    "Recipe_Mocha": ("BM_Espresso", "에스프레소 싱글샷"),
    "Recipe_Affogato": ("BM_Espresso", "에스프레소 싱글샷"),
    "Recipe_IcedAmericano": ("BM_Espresso", "더블 에스프레소"),
    "Recipe_Shakerato": ("BM_Espresso", "에스프레소 더블샷"),
    "Recipe_CubanCoffee": ("BM_Espresso", "에스프레소를 추출"),
    "Recipe_HoneyLatte": ("BM_Espresso", "에스프레소 싱글샷"),
    "Recipe_VanillaLatte": ("BM_Espresso", "에스프레소 싱글샷"),
    "Recipe_EspressoConPanna": ("BM_Espresso", "에스프레소를 데미타세"),
    "Recipe_ColdBrewConcentrate": ("BM_ColdBrew", "냉장 상태로 12-18시간"),
    "Recipe_NitroColdBrew": ("BM_ColdBrew", "콜드브루 원액"),
    "Recipe_PourOverV60": ("BM_PourOver", "페이퍼 필터"),
    "Recipe_FrenchPress": ("BM_FrenchPress", "플런저"),
    "Recipe_Aeropress": ("BM_AeroPress", "압착 추출"),
    "Recipe_MokaPot": ("BM_MokaPot", "하단 챔버"),
    "Recipe_TurkishCoffee": ("BM_Cezve", "체즈베"),
    "Recipe_VietnameseIcedCoffee": ("BM_Phin", "phin"),
    "Recipe_VietnameseEggCoffee": ("BM_Phin", "phin"),
    "Recipe_EthiopianBuna": ("BM_Jebena", "제베나"),
    "Recipe_MoroccanSpicedCoffee": ("BM_StovetopDecoction", "냄비에 넣고 약불로"),
}

BREW_PROPS = {
    "hasDoseGrams", "hasYieldMl", "hasBrewWaterMl", "hasWaterTempC", "hasBrewTimeSec",
    "hasPressureBar", "hasGrindSize", "hasEspressoShots", "hasBrewRatio",
}
RANGE_PROPS = {"hasDoseGrams", "hasYieldMl", "hasBrewWaterMl", "hasWaterTempC", "hasBrewTimeSec"}
GRIND_SIZES = {"ExtraFine", "Fine", "MediumFine", "Medium", "Coarse"}
BREW_CATEGORIES = {"Pressure", "Percolation", "Immersion", "Decoction"}


@pytest.fixture(scope="module")
def main_graph() -> Graph:
    """Existing source data: main RDF + every TTL except the brewing file."""
    g = Graph()
    g.parse(MAIN_RDF, format="xml")
    for ttl in sorted((ROOT / "data").glob("*.ttl")):
        if ttl != BREWING_TTL:
            g.parse(ttl, format="turtle")
    return g


@pytest.fixture(scope="module")
def brew_graph() -> Graph:
    assert BREWING_TTL.exists(), f"missing {BREWING_TTL}"
    g = Graph()
    g.parse(BREWING_TTL, format="turtle")
    return g


def instructions(main_graph: Graph, recipe: str) -> str:
    text = main_graph.value(COF[recipe], COF.hasInstructions)
    assert text is not None, f"{recipe} has no hasInstructions"
    return str(text)


def literal_value(g: Graph, subject: str, prop: str):
    vals = list(g.objects(COF[subject], COF[prop]))
    assert len(vals) <= 1, f"{subject}.{prop} has multiple values {vals}"
    return vals[0].toPython() if vals else None


# ── Schema ────────────────────────────────────────────────────────────

def test_brew_method_class_is_under_quality_and_processing(brew_graph: Graph) -> None:
    assert (COF.BrewMethod, RDF.type, OWL.Class) in brew_graph
    assert (COF.BrewMethod, RDFS.subClassOf, COF.QualityAndProcessing) in brew_graph


def test_uses_brew_method_property_declared(brew_graph: Graph) -> None:
    assert (COF.usesBrewMethod, RDF.type, OWL.ObjectProperty) in brew_graph
    assert (COF.usesBrewMethod, RDFS.domain, COF.Recipe) in brew_graph
    assert (COF.usesBrewMethod, RDFS.range, COF.BrewMethod) in brew_graph


def test_all_brew_data_properties_declared(brew_graph: Graph) -> None:
    declared = {str(s).split("#")[-1] for s in brew_graph.subjects(RDF.type, OWL.DatatypeProperty)}
    expected = {p + suffix for p in RANGE_PROPS for suffix in ("Min", "Max")}
    expected |= BREW_PROPS - RANGE_PROPS
    expected |= {"hasBrewCategory"}
    assert expected <= declared, f"missing: {expected - declared}"


def test_brew_methods_have_valid_category_and_description(brew_graph: Graph) -> None:
    methods = set(brew_graph.subjects(RDF.type, COF.BrewMethod))
    used = {m for m, _ in METHOD_EVIDENCE.values()}
    assert {str(m).split("#")[-1] for m in methods} >= used
    for m in methods:
        assert str(brew_graph.value(m, COF.hasBrewCategory)) in BREW_CATEGORIES, m
        assert brew_graph.value(m, COF.hasDescription), f"{m} lacks hasDescription"
        assert brew_graph.value(m, RDFS.label), f"{m} lacks rdfs:label"


# ── Provenance: every value backed by the recipe's own text ───────────

def test_every_referenced_recipe_exists_in_main_rdf(main_graph: Graph) -> None:
    for recipe in set(EVIDENCE) | set(METHOD_EVIDENCE):
        assert (COF[recipe], RDF.type, COF.Recipe) in main_graph, recipe


@pytest.mark.parametrize("recipe", sorted(EVIDENCE))
def test_evidence_snippets_appear_in_instructions(main_graph: Graph, recipe: str) -> None:
    text = instructions(main_graph, recipe)
    for item in EVIDENCE[recipe]:
        for snippet in item["ev"]:
            assert snippet in text, f"{recipe}.{item['prop']}: '{snippet}' not in instructions"


@pytest.mark.parametrize("recipe", sorted(METHOD_EVIDENCE))
def test_method_evidence_appears_in_instructions(main_graph: Graph, recipe: str) -> None:
    _, snippet = METHOD_EVIDENCE[recipe]
    assert snippet in instructions(main_graph, recipe)


@pytest.mark.parametrize("recipe", sorted(EVIDENCE))
def test_ttl_values_match_evidence(brew_graph: Graph, recipe: str) -> None:
    for item in EVIDENCE[recipe]:
        prop = item["prop"]
        if prop in RANGE_PROPS:
            assert literal_value(brew_graph, recipe, prop + "Min") == item["min"], (recipe, prop)
            assert literal_value(brew_graph, recipe, prop + "Max") == item.get("max"), (recipe, prop)
        else:
            assert literal_value(brew_graph, recipe, prop) == item["min"], (recipe, prop)


def test_no_unsourced_brew_values_in_ttl(brew_graph: Graph) -> None:
    """Any brew parameter in the TTL must be listed in EVIDENCE."""
    allowed = set()
    for recipe, items in EVIDENCE.items():
        for item in items:
            prop = item["prop"]
            if prop in RANGE_PROPS:
                allowed.add((recipe, prop + "Min"))
                if item.get("max") is not None:
                    allowed.add((recipe, prop + "Max"))
            else:
                allowed.add((recipe, prop))
    brew_prop_names = {p + s for p in RANGE_PROPS for s in ("Min", "Max")} | (BREW_PROPS - RANGE_PROPS)
    found = {
        (str(s).split("#")[-1], str(p).split("#")[-1])
        for s, p, o in brew_graph
        if isinstance(o, Literal) and str(p).split("#")[-1] in brew_prop_names
    }
    assert found == allowed, f"unsourced: {found - allowed}; missing: {allowed - found}"


def test_recipe_methods_match_evidence(brew_graph: Graph) -> None:
    found = {
        str(s).split("#")[-1]: str(o).split("#")[-1]
        for s, o in brew_graph.subject_objects(COF.usesBrewMethod)
    }
    assert found == {r: m for r, (m, _) in METHOD_EVIDENCE.items()}


def test_grind_sizes_use_controlled_vocabulary(brew_graph: Graph) -> None:
    for o in brew_graph.objects(None, COF.hasGrindSize):
        assert str(o) in GRIND_SIZES, o


def test_ranges_are_ordered(brew_graph: Graph) -> None:
    for p in RANGE_PROPS:
        for s, lo in brew_graph.subject_objects(COF[p + "Min"]):
            hi = brew_graph.value(s, COF[p + "Max"])
            if hi is not None:
                assert lo.toPython() <= hi.toPython(), (s, p)


# ── Pipeline: converter merges the TTL into the dashboard JSON ────────

@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("docs")
    env = {**os.environ, "COFFEELAND_OUT_DIR": str(out), "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "rdf_to_json.py")],
                   check=True, env=env, capture_output=True)
    return json.loads((out / "ontology_data.json").read_text(encoding="utf-8"))


def _find(tree: list[dict], name: str) -> dict | None:
    for node in tree:
        if node["name"] == name:
            return node
        hit = _find(node.get("children", []), name)
        if hit:
            return hit
    return None


def test_converter_places_brew_method_in_hierarchy(converted: dict) -> None:
    qp = _find(converted["classHierarchy"], "QualityAndProcessing")
    child = next((c for c in qp["children"] if c["name"] == "BrewMethod"), None)
    assert child is not None
    assert child["instanceCount"] >= len({m for m, _ in METHOD_EVIDENCE.values()})


def test_converter_exports_recipe_brew_params(converted: dict) -> None:
    props = converted["instanceDetails"]["Recipe_ClassicEspresso"]["properties"]
    assert props["hasDoseGramsMin"]["value"] == "18"
    assert props["hasWaterTempCMax"]["value"] == "94"
    assert props["usesBrewMethod"]["values"] == ["BM_Espresso"]
    # original data untouched
    assert "hasInstructions" in props


def test_converter_counts_data_properties(converted: dict) -> None:
    assert converted["meta"]["dataProperties"] >= 60 + 15


def test_converter_exports_uses_brew_method_edge(converted: dict) -> None:
    names = {p["name"] for p in converted["objectProperties"]}
    assert "usesBrewMethod" in names
