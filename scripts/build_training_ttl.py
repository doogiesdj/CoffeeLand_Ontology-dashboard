#!/usr/bin/env python3
"""Phase 3 — curriculum map: build data/coffeeland_training.ttl from existing data.

Source: the TrainingProgram list inside dashboard.html (name, level, modules,
duration, topics, summary, facts, region, provider, url). Nothing is invented:
  * every topic string is classified in TOPIC_SKILLS (possibly [] = not a skill,
    e.g. exam logistics or certificate administration),
  * every prerequisite link carries an evidence snippet found in the
    program's own facts,
  * each Skill lists the ontology classes it concerns (SKILL_CLASSES) — this is
    the curriculum → knowledge-graph bridge and is a reviewed design decision.
tests/test_training.py enforces completeness, evidence and freshness.

Usage:  python scripts/build_training_ttl.py          (writes the TTL)
        python scripts/build_training_ttl.py --check  (exit 1 if stale)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass

from rdflib import OWL, RDF, Graph

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD = os.path.join(BASE_DIR, "dashboard.html")
MAIN_RDF = os.path.join(BASE_DIR, "data", "coffeeland_final_v4.rdf")
OUT_TTL = os.path.join(BASE_DIR, "data", "coffeeland_training.ttl")

# ── Program ids (stable, ASCII) keyed by the exact `name` in the source ──
PROGRAM_IDS: dict[str, str] = {
    "Barista Basics": "TP_BaristaBasics",
    "Advanced Espresso": "TP_AdvancedEspresso",
    "Customer Service": "TP_CustomerService",
    "Food Safety & Hygiene": "TP_FoodSafety",
    "바리스타 2급 (KCA Barista Level 2)": "TP_KCA_Barista2",
    "바리스타 1급 (KCA Barista Level 1)": "TP_KCA_Barista1",
    "커피지도사 1·2급 (Coffee Instructor)": "TP_KCA_CoffeeInstructor",
    "로스트마스터 (Roast Master)": "TP_KCA_RoastMaster",
    "홈카페마스터 (Home Cafe Master)": "TP_KCA_HomeCafeMaster",
    "SCA 커피 스킬즈 프로그램 (CSP) — 한국": "TP_SCA_CSP_Korea",
    "Q 그레이더 (Q Arabica Grader) — 한국": "TP_QGrader_Korea",
    "국민내일배움카드 바리스타 양성과정": "TP_NaeilBaeum_Barista",
    "스타벅스 커피 마스터 (Coffee Master)": "TP_Starbucks_CoffeeMaster",
    "커피머신 엔지니어 1·2급": "TP_KCRO_MachineEngineer",
    "SCA 커피 스킬즈 프로그램 (Global CSP)": "TP_SCA_CSP_Global",
    "SCA 스킬즈 디플로마 (Skills Diploma)": "TP_SCA_SkillsDiploma",
    "공인 SCA 트레이너 (AST)": "TP_SCA_AST",
    "Q 그레이더 (Evolved / CVA 기반)": "TP_QGrader_Evolved",
    "Q 로부스타 그레이더 (R Grader)": "TP_CQI_RGrader",
    "CQI Q 프로세싱 (Level 1~3)": "TP_CQI_QProcessing",
    "커피 밸류 어세스먼트 (CVA for Cuppers)": "TP_SCA_CVA",
    "Barista Hustle 온라인 인증 과정": "TP_BaristaHustle_Online",
    "에스프레소 이탈리아노 스페셜리스트": "TP_IIAC_EspressoSpecialist",
    "J.C.Q.A. 커피 인스트럭터 검정 (일본)": "TP_JCQA_Instructor",
}

ORIGINS = {None: "InHouse", "KR": "Domestic", "INTL": "International"}

AREAS: dict[str, str] = {
    "Fundamentals": "커피 기초",
    "Brewing": "추출",
    "Milk": "우유·라떼아트",
    "Sensory": "관능·커핑",
    "Roasting": "로스팅",
    "GreenCoffee": "생두·가공",
    "Equipment": "장비·물",
    "Service": "서비스·판매",
    "Operations": "매장 운영",
    "Safety": "위생·안전",
}

# skill id → (area, Korean label, English label)
SKILLS: dict[str, tuple[str, str, str]] = {
    "SK_CoffeeFundamentals": ("Fundamentals", "커피 기초 지식", "Coffee Fundamentals"),
    "SK_CoffeeOrigins": ("Fundamentals", "산지 이해", "Coffee Origins"),
    "SK_CoffeeTerminology": ("Fundamentals", "커피 용어(영어)", "Coffee Terminology"),
    "SK_EspressoExtraction": ("Brewing", "에스프레소 추출", "Espresso Extraction"),
    "SK_EspressoCalibration": ("Brewing", "추출 보정(캘리브레이션)", "Espresso Calibration"),
    "SK_GrindProfile": ("Brewing", "분쇄 프로파일", "Grind Profile"),
    "SK_ExtractionTheory": ("Brewing", "추출 이론·설계", "Extraction Theory & Design"),
    "SK_FilterBrewing": ("Brewing", "핸드드립·추출 기구", "Filter Brewing & Brew Tools"),
    "SK_MilkSteaming": ("Milk", "우유 스티밍", "Milk Steaming"),
    "SK_LatteArt": ("Milk", "라떼아트", "Latte Art"),
    "SK_Cupping": ("Sensory", "커핑", "Cupping"),
    "SK_SensorySkills": ("Sensory", "감각 훈련(후각·미각·유기산)", "Sensory Skills"),
    "SK_FlavorEvaluation": ("Sensory", "향미 평가·프로파일링", "Flavor Evaluation"),
    "SK_CoffeeValueAssessment": ("Sensory", "CVA 품질 평가", "Coffee Value Assessment"),
    "SK_RoastLevelIdentification": ("Sensory", "로스트 레벨 식별", "Roast Level Identification"),
    "SK_Roasting": ("Roasting", "로스팅 이론·프로파일", "Roasting"),
    "SK_GreenCoffeeGrading": ("GreenCoffee", "생두 분류·결점두 그레이딩", "Green Coffee Grading"),
    "SK_Processing": ("GreenCoffee", "가공 방식·품질관리", "Processing"),
    "SK_EquipmentMaintenance": ("Equipment", "장비 관리·정비", "Equipment Maintenance"),
    "SK_WaterQuality": ("Equipment", "물·수질 관리", "Water Quality"),
    "SK_CustomerService": ("Service", "고객 서비스", "Customer Service"),
    "SK_Sales": ("Service", "판매·업셀링", "Sales & Upselling"),
    "SK_MenuPreparation": ("Operations", "메뉴 조리", "Menu Preparation"),
    "SK_CafeOperations": ("Operations", "카페 실무·운영", "Cafe Operations"),
    "SK_POSOperation": ("Operations", "POS 사용", "POS Operation"),
    "SK_Instruction": ("Operations", "교육·지도", "Instruction"),
    "SK_CompetitionPrep": ("Operations", "대회 준비", "Competition Preparation"),
    "SK_FoodSafety": ("Safety", "식품 위생·안전", "Food Safety & Hygiene"),
}

# Skill → ontology classes it concerns (curriculum ↔ knowledge-graph bridge)
SKILL_CLASSES: dict[str, list[str]] = {
    "SK_CoffeeFundamentals": ["CoffeeVariety", "ProcessingMethod", "RoastLevel", "BrewMethod"],
    "SK_CoffeeOrigins": ["Country", "Farm", "Harvest", "CoffeeVariety"],
    "SK_CoffeeTerminology": [],
    "SK_EspressoExtraction": ["BrewMethod", "EspressoMachine", "Grinder", "Recipe"],
    "SK_EspressoCalibration": ["BrewMethod", "EspressoMachine", "Grinder", "Recipe"],
    "SK_GrindProfile": ["Grinder"],
    "SK_ExtractionTheory": ["BrewMethod", "Recipe"],
    "SK_FilterBrewing": ["BrewMethod", "Recipe"],
    "SK_MilkSteaming": ["Milk", "EspressoMachine"],
    "SK_LatteArt": ["Milk", "BeverageMenu"],
    "SK_Cupping": ["FlavorNote", "QualityGrade", "CuppingCompetition"],
    "SK_SensorySkills": ["FlavorNote"],
    "SK_FlavorEvaluation": ["FlavorNote", "ProcessingMethod", "RoastLevel"],
    "SK_CoffeeValueAssessment": ["FlavorNote", "QualityGrade"],
    "SK_RoastLevelIdentification": ["RoastLevel"],
    "SK_Roasting": ["RoastLevel", "RoasterMachine"],
    "SK_GreenCoffeeGrading": ["QualityGrade", "CoffeeVariety"],
    "SK_Processing": ["ProcessingMethod", "ProcessingMill"],
    "SK_EquipmentMaintenance": ["EspressoMachine", "Grinder", "MaintenanceService"],
    "SK_WaterQuality": ["WaterFilter"],
    "SK_CustomerService": ["Consumer"],
    "SK_Sales": ["BeverageMenu"],
    "SK_MenuPreparation": ["Recipe", "BeverageMenu", "Ingredient"],
    "SK_CafeOperations": ["BeverageMenu", "Ingredient", "Consumable"],
    "SK_POSOperation": ["PosSystem"],
    "SK_Instruction": ["TrainingProgram"],
    "SK_CompetitionPrep": [],
    "SK_FoodSafety": ["Ingredient"],
}

# Every topic string in the source → skills taught. [] = not a skill
# (exam / certificate administration, sub-course names, delivery format).
TOPIC_SKILLS: dict[str, list[str]] = {
    # in-house programs
    "Espresso Fundamentals": ["SK_EspressoExtraction"],
    "Milk Steaming": ["SK_MilkSteaming"],
    "Coffee Origins": ["SK_CoffeeOrigins"],
    "Equipment Care": ["SK_EquipmentMaintenance"],
    "POS Usage": ["SK_POSOperation"],
    "Espresso Calibration": ["SK_EspressoCalibration"],
    "Grind Profile": ["SK_GrindProfile"],
    "Latte Art": ["SK_LatteArt"],
    "Cupping": ["SK_Cupping"],
    "Flavor Profiling": ["SK_FlavorEvaluation"],
    "Competition Prep": ["SK_CompetitionPrep"],
    "Communication Skills": ["SK_CustomerService"],
    "Complaint Handling": ["SK_CustomerService"],
    "Upselling Techniques": ["SK_Sales"],
    "HACCP Principles": ["SK_FoodSafety"],
    "Allergen Awareness": ["SK_FoodSafety"],
    "Temperature Control": ["SK_FoodSafety"],
    "Cleaning Procedures": ["SK_FoodSafety"],
    "Personal Hygiene": ["SK_FoodSafety"],
    "Certification": [],
    # KCA / domestic
    "커피학 개론": ["SK_CoffeeFundamentals"],
    "에스프레소 추출": ["SK_EspressoExtraction"],
    "우유 스티밍": ["SK_MilkSteaming"],
    "위생·매장 관리": ["SK_FoodSafety", "SK_CafeOperations"],
    "서비스 기술": ["SK_CustomerService"],
    "로스팅·향미 평가": ["SK_Roasting", "SK_FlavorEvaluation"],
    "추출 이론": ["SK_ExtractionTheory"],
    "에스프레소·카푸치노 시연": ["SK_EspressoExtraction", "SK_MilkSteaming"],
    "영어 커피 용어": ["SK_CoffeeTerminology"],
    "홈카페마스터 18h": [],
    "커피지도사 2급 27h": [],
    "커피지도사 1급 27h": [],
    "추출 설계": ["SK_ExtractionTheory"],
    "메뉴 조리 지도": ["SK_MenuPreparation", "SK_Instruction"],
    "고객 서비스 지도": ["SK_CustomerService", "SK_Instruction"],
    "생두 분류": ["SK_GreenCoffeeGrading"],
    "로스팅 이론": ["SK_Roasting"],
    "로스트 프로파일": ["SK_Roasting"],
    "결점두 식별": ["SK_GreenCoffeeGrading"],
    "향미 평가": ["SK_FlavorEvaluation"],
    "로스터리 카페 운영": ["SK_CafeOperations"],
    "추출 기구 활용": ["SK_FilterBrewing"],
    "핸드드립": ["SK_FilterBrewing"],
    "커피 기초 이론": ["SK_CoffeeFundamentals"],
    "머신 사용·위생 관리": ["SK_EquipmentMaintenance", "SK_FoodSafety"],
    "카페 실무": ["SK_CafeOperations"],
    "자격 검정 대비": [],
    "커피 지식": ["SK_CoffeeFundamentals"],
    "추출 실습": ["SK_EspressoExtraction"],
    "커핑·테이스팅": ["SK_Cupping"],
    "사이버 교육": [],
    "고객 경험": ["SK_CustomerService"],
    "머신 구조·부품": ["SK_EquipmentMaintenance"],
    "정비·트러블슈팅": ["SK_EquipmentMaintenance"],
    "수질·정수 관리": ["SK_WaterQuality"],
    "추출 압력·온도 세팅": ["SK_EquipmentMaintenance", "SK_EspressoCalibration"],
    "안전 관리": ["SK_FoodSafety"],
    # SCA CSP modules
    "Introduction to Coffee": ["SK_CoffeeFundamentals"],
    "Barista Skills": ["SK_EspressoExtraction", "SK_MilkSteaming"],
    "Brewing": ["SK_FilterBrewing"],
    "Green Coffee": ["SK_GreenCoffeeGrading"],
    "Roasting": ["SK_Roasting"],
    "Sensory Skills": ["SK_SensorySkills"],
    # Q / CQI / CVA
    "커핑 프로토콜": ["SK_Cupping"],
    "트라이앵귤레이션": ["SK_SensorySkills"],
    "아로마 식별": ["SK_SensorySkills"],
    "유기산 판별": ["SK_SensorySkills"],
    "결점두 그레이딩": ["SK_GreenCoffeeGrading"],
    "로스트 레벨 식별": ["SK_RoastLevelIdentification"],
    "CVA 평가 체계": ["SK_CoffeeValueAssessment"],
    "후각·미각 판별": ["SK_SensorySkills"],
    "유기산 식별": ["SK_SensorySkills"],
    "생두·원두 그레이딩": ["SK_GreenCoffeeGrading"],
    "후각·미각 감각": ["SK_SensorySkills"],
    "가공 방식 평가": ["SK_Processing"],
    "가공 표준 용어": ["SK_Processing"],
    "비교 커핑": ["SK_Cupping"],
    "주요 가공 방식": ["SK_Processing"],
    "후처리 품질관리 시스템": ["SK_Processing"],
    "플레이버 프로파일 설계": ["SK_FlavorEvaluation", "SK_Processing"],
    "CVA 프레임워크": ["SK_CoffeeValueAssessment"],
    "기술적(Technical) 평가": ["SK_CoffeeValueAssessment"],
    "기술서술적(Descriptive) 평가": ["SK_CoffeeValueAssessment"],
    "정서적(Affective) 평가": ["SK_CoffeeValueAssessment"],
    "외재적 가치 평가": ["SK_CoffeeValueAssessment"],
    # SCA diploma / AST — program administration, not skills
    "역할 기반 학습 경로": [],
    "모듈 인증서 누적": [],
    "전문 분야 심화": [],
    "국제 통용 디플로마": [],
    "경력·자격 심사": [],
    "프로그램 지식 평가": [],
    "온라인 과정 + 라이브 세션": [],
    "라이선스 계약": [],
    "지속적 전문성 개발(CPD)": [],
    # Barista Hustle / IIAC / JCQA
    "Advanced Coffee Making": ["SK_ExtractionTheory"],
    "The Water Course": ["SK_WaterQuality"],
    "The Espresso Machine": ["SK_EquipmentMaintenance"],
    "Advanced Espresso": ["SK_EspressoExtraction", "SK_ExtractionTheory"],
    "추출·균질성 이론": ["SK_ExtractionTheory"],
    "감각 훈련": ["SK_SensorySkills"],
    "이탈리안 에스프레소 역사": ["SK_CoffeeFundamentals"],
    "블렌드와 물": ["SK_WaterQuality"],
    "그라인딩·추출": ["SK_GrindProfile", "SK_EspressoExtraction"],
    "카푸치노": ["SK_MilkSteaming"],
    "관능 패널 테스트": ["SK_SensorySkills"],
    "커피 기초 지식": ["SK_CoffeeFundamentals"],
    "테이스팅 기법": ["SK_Cupping"],
    "품질 감별": ["SK_GreenCoffeeGrading"],
    "제조·판매 실무": ["SK_MenuPreparation", "SK_Sales"],
}

# program → [(prerequisite program, evidence snippet found in this program's facts)]
PREREQUISITES: dict[str, list[tuple[str, str]]] = {
    "TP_AdvancedEspresso": [("TP_BaristaBasics", "Barista Basics 이수")],
    "TP_KCA_Barista1": [("TP_KCA_Barista2", "협회 바리스타 2급 취득자")],
    "TP_KCA_CoffeeInstructor": [("TP_KCA_HomeCafeMaster", "하위 단계부터 순차 수강")],
    "TP_SCA_SkillsDiploma": [("TP_SCA_CSP_Global", "CSP 모듈 인증서 누적")],
    "TP_SCA_AST": [("TP_SCA_CSP_Global", "Intermediate + Professional 인증서 보유")],
}


@dataclass(frozen=True)
class Program:
    id: str
    name: str
    origin: str
    level: str
    modules: int | None
    duration: str
    provider: str | None
    summary: str
    url: str | None
    topics: tuple[str, ...]
    facts_text: str
    skills: tuple[str, ...]


# ── Minimal JS-literal → JSON (no code execution) ──────────────────────

def js_literal_to_json(src: str) -> str:
    """Convert a JS object/array literal (comments, single quotes, bare keys,
    trailing commas) into JSON text."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"":
            quote, j, buf = c, i + 1, []
            while src[j] != quote:
                if src[j] == "\\":
                    nxt = src[j + 1]
                    buf.append({"n": "\n", "t": "\t", "'": "'", '"': '"', "\\": "\\"}.get(nxt, nxt))
                    j += 2
                else:
                    buf.append(src[j])
                    j += 1
            out.append(json.dumps("".join(buf), ensure_ascii=False))
            i = j + 1
        elif src.startswith("//", i):
            i = src.index("\n", i)
        elif src.startswith("/*", i):
            i = src.index("*/", i) + 2
        elif c.isalpha() or c == "_":
            m = re.match(r"[A-Za-z_$][\w$]*", src[i:])
            word = m.group(0)
            rest = src[i + len(word):].lstrip()
            out.append(json.dumps(word) if rest.startswith(":") else word)
            i += len(word)
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[\]}])", r"\1", "".join(out))


def extract_training_programs(html: str) -> list[dict]:
    start = html.find("TrainingProgram: [")
    if start < 0:
        raise ValueError("TrainingProgram list not found in dashboard.html")
    i = html.index("[", start)
    depth, j, in_str = 0, i, None
    while True:  # find the matching ] while skipping strings/comments
        c = html[j]
        if in_str:
            if c == "\\":
                j += 1
            elif c == in_str:
                in_str = None
        elif c in "'\"":
            in_str = c
        elif html.startswith("//", j):
            j = html.index("\n", j)
            continue
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return json.loads(js_literal_to_json(html[i:j + 1]))


# ── Building ───────────────────────────────────────────────────────────

def build_programs(raw: list[dict]) -> list[Program]:
    programs = []
    for p in raw:
        name = p["name"]
        if name not in PROGRAM_IDS:
            raise ValueError(f"no id for program {name!r} — add it to PROGRAM_IDS")
        missing = [t for t in p["topics"] if t not in TOPIC_SKILLS]
        if missing:
            raise ValueError(f"{name}: unclassified topics {missing}")
        skills: list[str] = []
        for t in p["topics"]:
            for s in TOPIC_SKILLS[t]:
                if s not in SKILLS:
                    raise ValueError(f"unknown skill {s}")
                if s not in skills:
                    skills.append(s)
        modules = int(p["modules"]) if str(p.get("modules", "")).isdigit() else None
        programs.append(Program(
            id=PROGRAM_IDS[name], name=name, origin=ORIGINS[p.get("region")],
            level=p["level"], modules=modules, duration=p["duration"],
            provider=p.get("provider"), summary=p["summary"], url=p.get("url"),
            topics=tuple(p["topics"]),
            facts_text=" ".join(f"{k}: {v}" for k, v in p.get("facts", [])),
            skills=tuple(skills),
        ))
    return programs


def ontology_classes() -> set[str]:
    g = Graph()
    g.parse(MAIN_RDF, format="xml")
    for ttl in sorted(os.listdir(os.path.join(BASE_DIR, "data"))):
        path = os.path.join(BASE_DIR, "data", ttl)
        if ttl.endswith(".ttl") and os.path.abspath(path) != os.path.abspath(OUT_TTL):
            g.parse(path, format="turtle")
    return {str(s).split("#")[-1] for s in g.subjects(RDF.type, OWL.Class)}


def validate(programs: list[Program], classes: set[str]) -> None:
    ids = {p.id for p in programs}
    for skill, cls_list in SKILL_CLASSES.items():
        unknown = [c for c in cls_list if c not in classes and c not in {"Skill"}]
        if unknown:
            raise ValueError(f"{skill} → unknown classes {unknown}")
    if set(SKILL_CLASSES) != set(SKILLS):
        raise ValueError("SKILL_CLASSES and SKILLS must list the same skills")
    by_id = {p.id: p for p in programs}
    for pid, reqs in PREREQUISITES.items():
        for req, snippet in reqs:
            if pid not in ids or req not in ids:
                raise ValueError(f"prerequisite {pid} ← {req}: unknown program")
            if snippet not in by_id[pid].facts_text:
                raise ValueError(f"{pid}: evidence '{snippet}' not in its facts")


# ── TTL rendering ──────────────────────────────────────────────────────

HEADER = """@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix cof:  <http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#> .

# ================================================================
# 커피랜드 온톨로지 — 3단계: 교육 과정(커리큘럼) 지도
# 자동 생성 파일 — 직접 고치지 말고 scripts/build_training_ttl.py 를 수정한 뒤
#   python scripts/build_training_ttl.py
# 로 다시 만드세요. (tests/test_training.py 가 최신 상태인지 검사합니다)
#
# 출처: dashboard.html 의 TrainingProgram 목록 (topics / facts / 기본 정보)
# ================================================================

cof:Skill a owl:Class ;
    rdfs:subClassOf cof:ShopOperation ;
    rdfs:label "기술(역량)"@ko , "Skill"@en ;
    rdfs:comment "교육 과정에서 배우는 역량. relatesToConcept 로 온톨로지의 관련 클래스와 연결된다."@ko .

cof:teachesSkill a owl:ObjectProperty ;
    rdfs:domain cof:TrainingProgram ; rdfs:range cof:Skill ;
    rdfs:label "가르치는 기술"@ko .

cof:hasPrerequisite a owl:ObjectProperty ;
    rdfs:domain cof:TrainingProgram ; rdfs:range cof:TrainingProgram ;
    rdfs:label "선수 과정"@ko ;
    rdfs:comment "이 과정을 듣기 전에 이수·취득해야 하는 과정 (원문 facts 근거)."@ko .

cof:relatesToConcept a owl:ObjectProperty ;
    rdfs:domain cof:Skill ;
    rdfs:label "관련 개념"@ko ;
    rdfs:comment "기술이 다루는 온톨로지 클래스 (OWL 2 punning: 클래스 IRI 를 값으로 사용)."@ko .

cof:hasSkillArea a owl:DatatypeProperty ; rdfs:domain cof:Skill ; rdfs:range xsd:string ;
    rdfs:comment "Fundamentals | Brewing | Milk | Sensory | Roasting | GreenCoffee | Equipment | Service | Operations | Safety"@ko .
cof:hasProgramName a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:string .
cof:hasProgramOrigin a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:string ;
    rdfs:comment "InHouse(사내) | Domestic(국내) | International(해외)"@ko .
cof:hasProgramLevel a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:string .
cof:hasModuleCount a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:integer .
cof:hasDuration a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:string .
cof:hasTopic a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:string ;
    rdfs:comment "원문 주제 표기 그대로 (teachesSkill 분류의 근거)."@ko .
cof:hasWebsite a owl:DatatypeProperty ; rdfs:domain cof:TrainingProgram ; rdfs:range xsd:anyURI .
"""


def _lit(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def render_ttl(programs: list[Program]) -> str:
    lines = [HEADER, "# ── 기술 ──"]
    for sid, (area, ko, en) in SKILLS.items():
        rel = SKILL_CLASSES[sid]
        parts = [f"cof:{sid} a owl:NamedIndividual , cof:Skill",
                 f"rdfs:label {_lit(ko)}@ko , {_lit(en)}@en",
                 f"cof:hasSkillArea {_lit(area)}^^xsd:string"]
        if rel:
            parts.append("cof:relatesToConcept " + " , ".join(f"cof:{c}" for c in rel))
        lines.append(" ;\n    ".join(parts) + " .")
    lines += ["", "# ── 교육 과정 ──"]
    for p in programs:
        parts = [f"cof:{p.id} a owl:NamedIndividual , cof:TrainingProgram",
                 f"rdfs:label {_lit(p.name)}",
                 f"cof:hasProgramName {_lit(p.name)}^^xsd:string",
                 f"cof:hasProgramOrigin {_lit(p.origin)}^^xsd:string",
                 f"cof:hasProgramLevel {_lit(p.level)}^^xsd:string",
                 f"cof:hasDuration {_lit(p.duration)}^^xsd:string",
                 f"cof:hasDescription {_lit(p.summary)}^^xsd:string"]
        if p.modules is not None:
            parts.append(f"cof:hasModuleCount {p.modules}")
        if p.provider:
            parts.append(f"cof:hasProvider {_lit(p.provider)}^^xsd:string")
        if p.url:
            parts.append(f"cof:hasWebsite {_lit(p.url)}^^xsd:anyURI")
        parts.append("cof:hasTopic " + " , ".join(f"{_lit(t)}^^xsd:string" for t in p.topics))
        if p.skills:
            parts.append("cof:teachesSkill " + " , ".join(f"cof:{s}" for s in p.skills))
        reqs = PREREQUISITES.get(p.id, [])
        if reqs:
            parts.append("cof:hasPrerequisite " + " , ".join(f"cof:{r}" for r, _ in reqs))
        lines.append(" ;\n    ".join(parts) + " .")
    return "\n".join(lines) + "\n"


def build() -> str:
    with open(DASHBOARD, encoding="utf-8") as f:
        html = f.read()
    programs = build_programs(extract_training_programs(html))
    validate(programs, ontology_classes())
    return render_ttl(programs)


def main(argv: list[str]) -> int:
    content = build()
    if "--check" in argv:
        with open(OUT_TTL, encoding="utf-8") as f:
            stale = f.read() != content
        if stale:
            sys.stderr.write("coffeeland_training.ttl is stale — run scripts/build_training_ttl.py\n")
        return 1 if stale else 0
    with open(OUT_TTL, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    sys.stdout.write(f"wrote {OUT_TTL}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
