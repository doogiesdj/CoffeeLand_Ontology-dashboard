"""Phase 3 (curriculum map) — completeness, evidence, freshness and pipeline tests."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from rdflib import RDF, RDFS, Graph, Namespace

ROOT = Path(__file__).resolve().parent.parent
TRAINING_TTL = ROOT / "data" / "coffeeland_training.ttl"
COF = Namespace("http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#")

_spec = importlib.util.spec_from_file_location("build_training_ttl", ROOT / "scripts" / "build_training_ttl.py")
bt = importlib.util.module_from_spec(_spec)
sys.modules["build_training_ttl"] = bt
_spec.loader.exec_module(bt)


@pytest.fixture(scope="module")
def raw() -> list[dict]:
    return bt.extract_training_programs((ROOT / "dashboard.html").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ttl() -> Graph:
    assert TRAINING_TTL.exists(), "run: python scripts/build_training_ttl.py"
    g = Graph()
    g.parse(TRAINING_TTL, format="turtle")
    return g


def local(uri) -> str:
    return str(uri).split("#")[-1]


def skills_of(g: Graph, pid: str) -> set[str]:
    return {local(o) for o in g.objects(COF[pid], COF.teachesSkill)}


# ── Source parsing ──

def test_parser_reads_all_programs_without_executing_code(raw: list[dict]) -> None:
    assert len(raw) == 24
    assert raw[0]["name"] == "Barista Basics" and raw[0]["topics"][0] == "Espresso Fundamentals"
    # facts are [key, value] pairs; strings with commas/quotes survive
    assert ["선수 과정", "Barista Basics 이수"] in raw[1]["facts"]


def test_js_literal_parser_handles_comments_quotes_trailing_commas() -> None:
    src = "[ // c\n { a:'it\\'s', b:\"x, y\", c:['p','q',], }, ]"
    assert json.loads(bt.js_literal_to_json(src)) == [{"a": "it's", "b": "x, y", "c": ["p", "q"]}]


# ── Completeness ──

def test_every_program_has_an_id(raw: list[dict]) -> None:
    assert {p["name"] for p in raw} == set(bt.PROGRAM_IDS)


def test_every_topic_is_classified_and_no_dead_entries(raw: list[dict]) -> None:
    topics = {t for p in raw for t in p["topics"]}
    assert topics - set(bt.TOPIC_SKILLS) == set()
    assert set(bt.TOPIC_SKILLS) - topics == set()


def test_every_skill_is_taught_somewhere(raw: list[dict]) -> None:
    taught = {s for p in raw for t in p["topics"] for s in bt.TOPIC_SKILLS[t]}
    assert set(bt.SKILLS) - taught == set()


def test_skill_areas_and_class_links_are_valid() -> None:
    assert set(bt.SKILL_CLASSES) == set(bt.SKILLS)
    for sid, (area, ko, en) in bt.SKILLS.items():
        assert area in bt.AREAS and ko and en, sid
    classes = bt.ontology_classes()
    for sid, cls_list in bt.SKILL_CLASSES.items():
        assert set(cls_list) <= classes, (sid, set(cls_list) - classes)


def test_prerequisite_evidence_in_facts(raw: list[dict]) -> None:
    by_id = {p.id: p for p in bt.build_programs(raw)}
    for pid, reqs in bt.PREREQUISITES.items():
        for req, snippet in reqs:
            assert snippet in by_id[pid].facts_text, (pid, snippet)
            assert req in by_id


def test_committed_ttl_is_up_to_date() -> None:
    assert TRAINING_TTL.read_text(encoding="utf-8") == bt.build()


# ── Spot checks (hand-written from the source) ──

def test_advanced_espresso(ttl: Graph) -> None:
    # topics: Espresso Calibration, Grind Profile, Latte Art, Cupping, Flavor Profiling, Competition Prep
    assert skills_of(ttl, "TP_AdvancedEspresso") == {
        "SK_EspressoCalibration", "SK_GrindProfile", "SK_LatteArt", "SK_Cupping",
        "SK_FlavorEvaluation", "SK_CompetitionPrep"}
    assert {local(o) for o in ttl.objects(COF.TP_AdvancedEspresso, COF.hasPrerequisite)} == {"TP_BaristaBasics"}


def test_kca_level_chain_and_origin(ttl: Graph) -> None:
    assert (COF.TP_KCA_Barista1, COF.hasPrerequisite, COF.TP_KCA_Barista2) in ttl
    assert str(ttl.value(COF.TP_KCA_Barista2, COF.hasProgramOrigin)) == "Domestic"
    assert str(ttl.value(COF.TP_BaristaBasics, COF.hasProgramOrigin)) == "InHouse"
    assert str(ttl.value(COF.TP_SCA_AST, COF.hasProgramOrigin)) == "International"


def test_q_grader_korea_skills(ttl: Graph) -> None:
    assert skills_of(ttl, "TP_QGrader_Korea") == {
        "SK_Cupping", "SK_SensorySkills", "SK_GreenCoffeeGrading", "SK_RoastLevelIdentification"}


def test_admin_only_programs_teach_nothing_invented(ttl: Graph) -> None:
    # SCA Skills Diploma topics are all certificate administration
    assert skills_of(ttl, "TP_SCA_SkillsDiploma") == set()


def test_skill_concepts_bridge_to_graph(ttl: Graph) -> None:
    rel = {local(o) for o in ttl.objects(COF.SK_EspressoExtraction, COF.relatesToConcept)}
    assert rel == {"BrewMethod", "EspressoMachine", "Grinder", "Recipe"}


def test_original_topics_preserved(ttl: Graph, raw: list[dict]) -> None:
    for p in raw:
        stored = {str(o) for o in ttl.objects(COF[bt.PROGRAM_IDS[p["name"]]], COF.hasTopic)}
        assert stored == set(p["topics"]), p["name"]


def test_schema(ttl: Graph) -> None:
    assert (COF.Skill, RDFS.subClassOf, COF.ShopOperation) in ttl
    assert len(set(ttl.subjects(RDF.type, COF.TrainingProgram))) == 24
    assert len(set(ttl.subjects(RDF.type, COF.Skill))) == len(bt.SKILLS)


# ── Pipeline ──

@pytest.fixture(scope="module")
def converted(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("docs")
    env = {**os.environ, "COFFEELAND_OUT_DIR": str(out), "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "rdf_to_json.py")],
                   check=True, env=env, capture_output=True)
    return json.loads((out / "ontology_data.json").read_text(encoding="utf-8"))


def test_converter_exports_training(converted: dict) -> None:
    shop = next(n for n in converted["classHierarchy"] if n["name"] == "ShopOperation")
    children = {c["name"]: c for c in shop["children"]}
    assert children["TrainingProgram"]["instanceCount"] == 24
    assert children["Skill"]["instanceCount"] == len(bt.SKILLS)
    ae = converted["instanceDetails"]["TP_AdvancedEspresso"]
    assert ae["label"] == "Advanced Espresso"
    assert ae["properties"]["hasPrerequisite"]["values"] == ["TP_BaristaBasics"]
    assert "SK_GrindProfile" in ae["properties"]["teachesSkill"]["values"]
    sk = converted["instanceDetails"]["SK_EspressoExtraction"]
    assert sk["label"] == "에스프레소 추출"
    assert set(sk["properties"]["relatesToConcept"]["values"]) == {"BrewMethod", "EspressoMachine", "Grinder", "Recipe"}


def test_converter_does_not_truncate_skills(converted: dict) -> None:
    """instanceDetails keeps at most 10 object values — programs must fit."""
    for name, d in converted["instanceDetails"].items():
        if "TrainingProgram" in d["types"]:
            assert len(d["properties"].get("teachesSkill", {}).get("values", [])) <= 10, name
