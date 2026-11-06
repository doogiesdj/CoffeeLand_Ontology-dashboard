#!/usr/bin/env python3
"""Phase 2 — flavor layer: build data/coffeeland_flavor.ttl from existing data.

Sources (nothing is invented; every tag comes from text already in the project):
  1. dashboard.html  window.COUNTRY_DATA[<Country>].flavor   (Korean list)
  2. dashboard.html  window.HARVEST_DATA[<Harvest_Region>].flavor (English, comma list)
  3. RDF rdfs:comment on ProcessingMethod / RoastLevel / QualityGrade instances

Every source fragment must be classified in FRAGMENT_TAGS (possibly as [] =
deliberately ignored). Comment-based tags carry an evidence snippet that must
appear verbatim in the comment. tests/test_flavor.py enforces both rules and
that the committed TTL matches this script's output.

Usage:  python scripts/build_flavor_ttl.py            (writes data/coffeeland_flavor.ttl)
        python scripts/build_flavor_ttl.py --check    (exit 1 if TTL is stale)
"""

from __future__ import annotations

import glob
import os
import re
import sys
from dataclasses import dataclass

from rdflib import RDFS, Graph, Namespace

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD = os.path.join(BASE_DIR, "dashboard.html")
MAIN_RDF = os.path.join(BASE_DIR, "data", "coffeeland_final_v4.rdf")
OUT_TTL = os.path.join(BASE_DIR, "data", "coffeeland_flavor.ttl")
NS = "http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#"
COF = Namespace(NS)

# ── Vocabulary ──────────────────────────────────────────────────────────
# Top-level categories follow the SCA/WCR Coffee Taster's Flavor Wheel.
CATEGORIES: dict[str, tuple[str, str]] = {
    "Floral": ("꽃", "Floral"),
    "Fruity": ("과일", "Fruity"),
    "SourFermented": ("신맛·발효", "Sour / Fermented"),
    "GreenVegetative": ("풀·채소", "Green / Vegetative"),
    "Roasted": ("로스팅", "Roasted"),
    "Spices": ("향신료", "Spices"),
    "NuttyCocoa": ("견과·코코아", "Nutty / Cocoa"),
    "Sweet": ("단맛", "Sweet"),
    "Other": ("기타(흙·나무)", "Other (Earthy / Woody)"),
}

# note id → (category, Korean label, English label)
NOTES: dict[str, tuple[str, str, str]] = {
    "FN_Floral": ("Floral", "꽃향", "Floral"),
    "FN_Jasmine": ("Floral", "재스민", "Jasmine"),
    "FN_Rose": ("Floral", "장미", "Rose"),
    "FN_Fruity": ("Fruity", "과일향", "Fruity"),
    "FN_Berry": ("Fruity", "베리", "Berry"),
    "FN_Blueberry": ("Fruity", "블루베리", "Blueberry"),
    "FN_Blackcurrant": ("Fruity", "블랙커런트", "Blackcurrant"),
    "FN_RedBerry": ("Fruity", "레드베리", "Red Berry"),
    "FN_DriedFruit": ("Fruity", "건과일", "Dried Fruit"),
    "FN_Citrus": ("Fruity", "시트러스", "Citrus"),
    "FN_Orange": ("Fruity", "오렌지", "Orange"),
    "FN_Lemon": ("Fruity", "레몬", "Lemon"),
    "FN_Grapefruit": ("Fruity", "자몽", "Grapefruit"),
    "FN_Bergamot": ("Fruity", "베르가못", "Bergamot"),
    "FN_Peach": ("Fruity", "복숭아", "Peach"),
    "FN_StoneFruit": ("Fruity", "핵과류", "Stone Fruit"),
    "FN_Apple": ("Fruity", "사과", "Apple"),
    "FN_GreenApple": ("Fruity", "청사과", "Green Apple"),
    "FN_Grape": ("Fruity", "적포도", "Red Grape"),
    "FN_Plum": ("Fruity", "자두·매실", "Plum"),
    "FN_TropicalFruit": ("Fruity", "열대과일", "Tropical Fruit"),
    "FN_RoseHip": ("Fruity", "로즈힙", "Rose Hip"),
    "FN_Tomato": ("Fruity", "토마토", "Tomato"),
    "FN_Winey": ("SourFermented", "와인", "Winey"),
    "FN_Herbal": ("GreenVegetative", "허브", "Herbal"),
    "FN_Grassy": ("GreenVegetative", "풀내", "Grassy"),
    "FN_Tobacco": ("Roasted", "담배", "Tobacco"),
    "FN_Smoky": ("Roasted", "스모키", "Smoky"),
    "FN_Spice": ("Spices", "향신료", "Spice"),
    "FN_Chocolate": ("NuttyCocoa", "초콜릿", "Chocolate"),
    "FN_DarkChocolate": ("NuttyCocoa", "다크초콜릿", "Dark Chocolate"),
    "FN_MilkChocolate": ("NuttyCocoa", "밀크초콜릿", "Milk Chocolate"),
    "FN_Nutty": ("NuttyCocoa", "견과류", "Nutty"),
    "FN_Hazelnut": ("NuttyCocoa", "헤이즐넛", "Hazelnut"),
    "FN_Caramel": ("Sweet", "캐러멜", "Caramel"),
    "FN_BrownSugar": ("Sweet", "흑설탕", "Brown Sugar"),
    "FN_Honey": ("Sweet", "꿀", "Honey"),
    "FN_Sweet": ("Sweet", "단맛", "Sweet"),
    "FN_Earthy": ("Other", "흙내", "Earthy"),
    "FN_Woody": ("Other", "나무", "Woody"),
}

ACIDITY_LEVELS = ("Low", "Medium", "High")
BODY_LEVELS = ("Light", "Medium", "Full")

# Tag syntax: a note id ("FN_Jasmine"), "acidity:<level>" or "body:<level>".
# [] = fragment is read but deliberately not mapped (cleanliness, complexity,
# texture words like "silky", or region-specific remarks).
FRAGMENT_TAGS: dict[str, list[str]] = {
    # ── HARVEST_DATA (English; matched lower-case) ──
    "apple": ["FN_Apple"],
    "balanced acidity": ["acidity:Medium"],
    "balanced body": ["body:Medium"],
    "balanced medium acidity": ["acidity:Medium"],
    "bergamot": ["FN_Bergamot"],
    "berry": ["FN_Berry"],
    "berry jam": ["FN_Berry"],
    "blackcurrant": ["FN_Blackcurrant"],
    "blueberry": ["FN_Blueberry"],
    "bold": [],
    "bright acidity": ["acidity:High"],
    "bright citrus": ["FN_Citrus"],
    "bright citrus acidity": ["FN_Citrus", "acidity:High"],
    "bright clean acidity": ["acidity:High"],
    "bright lively acidity": ["acidity:High"],
    "brilliant transparent acidity": ["acidity:High"],
    "brown sugar": ["FN_BrownSugar"],
    "caramel": ["FN_Caramel"],
    "cedar": ["FN_Woody"],
    "chocolate": ["FN_Chocolate"],
    "citrus": ["FN_Citrus"],
    "clean": [],
    "clean acidity": [],
    "clean bright acidity": ["acidity:High"],
    "clean cup": [],
    "clean finish": [],
    "complex": [],
    "complex acidity": [],
    "creamy body": [],
    "dark chocolate": ["FN_DarkChocolate"],
    "dried fruit": ["FN_DriedFruit"],
    "earthy": ["FN_Earthy"],
    "elegant body": [],
    "exceptionally clean finish": [],
    "floral": ["FN_Floral"],
    "fruity": ["FN_Fruity"],
    "full body": ["body:Full"],
    "gentle citrus": ["FN_Citrus"],
    "grapefruit": ["FN_Grapefruit"],
    "hazelnut": ["FN_Hazelnut"],
    "heavy body": ["body:Full"],
    "heavy full body": ["body:Full"],
    "herbal": ["FN_Herbal"],
    "honey": ["FN_Honey"],
    "jasmine": ["FN_Jasmine"],
    "lemon zest": ["FN_Lemon"],
    "light citrus": ["FN_Citrus"],
    "low acidity": ["acidity:Low"],
    "mango": ["FN_TropicalFruit"],
    "medium acidity": ["acidity:Medium"],
    "medium body": ["body:Medium"],
    "mild": [],
    "mild acidity": ["acidity:Low"],
    "mild earthiness": ["FN_Earthy"],
    "milk chocolate": ["FN_MilkChocolate"],
    "nutty": ["FN_Nutty"],
    "peach": ["FN_Peach"],
    "plum": ["FN_Plum"],
    "red apple": ["FN_Apple"],
    "red berry": ["FN_RedBerry"],
    "red fruit": ["FN_Fruity"],
    "rose hip": ["FN_RoseHip"],
    "silky body": [],
    "smooth balanced body": ["body:Medium"],
    "smooth body": [],
    "smooth low acidity": ["acidity:Low"],
    "soft acidity": ["acidity:Low"],
    "sparkling acidity": ["acidity:High"],
    "spice": ["FN_Spice"],
    "spicy": ["FN_Spice"],
    "stone fruit": ["FN_StoneFruit"],
    "subtle sweetness": ["FN_Sweet"],
    "sweet": ["FN_Sweet"],
    "syrupy body": ["body:Full"],
    "tea-like body": ["body:Light"],
    "tobacco": ["FN_Tobacco"],
    "tomato": ["FN_Tomato"],
    "wild and complex": [],
    "wild complexity": [],
    "wine": ["FN_Winey"],
    "wine notes": ["FN_Winey"],
    "wine-like acidity": ["FN_Winey"],
    # ── COUNTRY_DATA (Korean) ──
    "강한 바디감": ["body:Full"],
    "강한 산미": ["acidity:High"],
    "강한 쓴맛": [],
    "건과일": ["FN_DriedFruit"],
    "견과류": ["FN_Nutty"],
    "과일향": ["FN_Fruity"],
    "균형잡힌 바디": ["body:Medium"],
    "균형잡힌 산미": ["acidity:Medium"],
    "꽃향": ["FN_Floral"],
    "꽃향(Floral)": ["FN_Floral"],
    "꿀": ["FN_Honey"],
    "낮은 산미": ["acidity:Low"],
    "낮은 산미(산성도 약함)": ["acidity:Low"],
    "너티": ["FN_Nutty"],
    "높은 바디": ["body:Full"],
    "다크 초콜릿": ["FN_DarkChocolate"],
    "다크초콜릿": ["FN_DarkChocolate"],
    "달콤한 산미": [],
    "독특한 몬순 캐릭터": [],
    "레드베리": ["FN_RedBerry"],
    "매실": ["FN_Plum"],
    "무거운 바디": ["body:Full"],
    "밀크초콜릿": ["FN_MilkChocolate"],
    "밝은 과일향(Jinotega)": ["FN_Fruity"],
    "밝은 산미": ["acidity:High"],
    "베르가못": ["FN_Bergamot"],
    "베리 류": ["FN_Berry"],
    "베리, 과일향(Bugisu Arabica)": ["FN_Berry", "FN_Fruity"],
    "복숭아": ["FN_Peach"],
    "부드러운 산미": ["acidity:Low"],
    "브라운슈가": ["FN_BrownSugar"],
    "블랙커런트": ["FN_Blackcurrant"],
    "블루베리": ["FN_Blueberry"],
    "소프트 산미": ["acidity:Low"],
    "순한 산미": ["acidity:Low"],
    "스파이스": ["FN_Spice"],
    "시트러스": ["FN_Citrus"],
    "시트러스(오렌지·레몬)": ["FN_Citrus", "FN_Orange", "FN_Lemon"],
    "어시(Earthy)": ["FN_Earthy"],
    "열대과일": ["FN_TropicalFruit"],
    "오렌지 산미": ["FN_Orange"],
    "오렌지·레몬 산미": ["FN_Orange", "FN_Lemon"],
    "와인": ["FN_Winey"],
    "와인 노트": ["FN_Winey"],
    "은은한 단맛": ["FN_Sweet"],
    "응축된 풍미(Peaberry)": [],
    "자몽": ["FN_Grapefruit"],
    "장미": ["FN_Rose"],
    "재스민": ["FN_Jasmine"],
    "저산미": ["acidity:Low"],
    "적포도": ["FN_Grape"],
    "청사과 산미": ["FN_GreenApple"],
    "초콜릿": ["FN_Chocolate"],
    "카라멜": ["FN_Caramel"],
    "캐러멜": ["FN_Caramel"],
    "클린한 산미": [],
    "토마토": ["FN_Tomato"],
    "트로피칼": ["FN_TropicalFruit"],
    "풀바디": ["body:Full"],
    "허니·달콤함": ["FN_Honey", "FN_Sweet"],
    "허브": ["FN_Herbal"],
    "헤이즐넛": ["FN_Hazelnut"],
    "흙내(Earthy)": ["FN_Earthy"],
    "흙향, 풀내(Robusta)": ["FN_Earthy", "FN_Grassy"],
    "흙향, 향신료향": ["FN_Earthy", "FN_Spice"],
}

# Instances described by an rdfs:comment: (tag, evidence snippet in that comment)
COMMENT_TAGS: dict[str, list[tuple[str, str]]] = {
    "Washed_Process": [("acidity:High", "산미가 높음")],
    "Natural_Process": [("FN_Fruity", "과일향"), ("body:Full", "바디감이 풍부함")],
    "Honey_Process": [("FN_Sweet", "단맛"), ("acidity:Medium", "단맛과 산미의 균형")],
    "WetHulled_Process": [("acidity:Low", "낮은 산미"), ("body:Full", "무거운 바디")],
    "Black_Honey_Process": [("FN_Sweet", "단맛"), ("body:Full", "바디감이 가장 진함")],
    "Light_Roast": [("acidity:High", "산지 고유의 산미와 향미가 가장 뚜렷")],
    "Medium_Roast": [("acidity:Medium", "산미와 바디감의 균형"), ("body:Medium", "산미와 바디감의 균형")],
    "Medium_Dark_Roast": [("FN_Sweet", "단맛"), ("body:Full", "바디감이 강조됨")],
    "Dark_Roast": [("FN_Smoky", "스모키"), ("FN_Caramel", "카라멜 풍미")],
    "Espresso_Roast": [("acidity:Low", "산미를 낮춰"), ("body:Full", "바디감을 강화")],
    "QG_Guatemala_SHB": [("acidity:High", "산미가 밝음")],
}


@dataclass(frozen=True)
class Profile:
    """Flavor profile of one RDF instance."""
    subject: str
    notes: tuple[str, ...]
    acidity: str | None
    body: str | None
    source: str


# ── Source extraction ───────────────────────────────────────────────────

_TOKEN = re.compile(
    r"(?P<key>'(?P<name>[A-Za-z_]+)'\s*:\s*\{)"
    r"|(?P<open>\{)|(?P<close>\})"
    r"|flavor\s*:\s*(?P<flavor>\[[^\]]*\]|'[^']*')"
)


def js_object_flavors(html: str, var_name: str) -> dict[str, str]:
    """Return {top-level key: raw flavor literal} for `window.<var_name> = {...}`."""
    start = html.find(f"window.{var_name} = {{")
    if start < 0:
        raise ValueError(f"window.{var_name} not found in dashboard.html")
    pos = html.index("{", start)
    depth, current, out = 0, None, {}
    for m in _TOKEN.finditer(html, pos):
        if m.group("key"):
            if depth == 1:
                current = m.group("name")
            depth += 1
        elif m.group("open"):
            depth += 1
        elif m.group("close"):
            depth -= 1
            if depth == 0:
                return out
        elif m.group("flavor") and depth == 2 and current:
            out[current] = m.group("flavor")
    raise ValueError(f"window.{var_name} is not closed")


def country_fragments(raw: str) -> list[str]:
    return [s.strip() for s in re.findall(r"'([^']*)'", raw)]


def harvest_fragments(raw: str) -> list[str]:
    return [s.strip().lower() for s in raw.strip("'").split(",") if s.strip()]


def load_rdf() -> Graph:
    g = Graph()
    g.parse(MAIN_RDF, format="xml")
    for ttl in sorted(glob.glob(os.path.join(BASE_DIR, "data", "*.ttl"))):
        if os.path.abspath(ttl) != os.path.abspath(OUT_TTL):
            g.parse(ttl, format="turtle")
    return g


# ── Profile building ────────────────────────────────────────────────────

def _apply(subject: str, tags: list[str], source: str) -> Profile:
    notes: list[str] = []
    levels: dict[str, str] = {}
    for tag in tags:
        if tag.startswith(("acidity:", "body:")):
            kind, level = tag.split(":")
            if kind in levels and levels[kind] != level:
                raise ValueError(f"{subject}: conflicting {kind} {levels[kind]} vs {level}")
            levels[kind] = level
        elif tag in NOTES:
            if tag not in notes:
                notes.append(tag)
        else:
            raise ValueError(f"{subject}: unknown tag {tag}")
    return Profile(subject, tuple(notes), levels.get("acidity"), levels.get("body"), source)


def unclassified_fragments(fragments: list[str]) -> list[str]:
    return [f for f in fragments if f not in FRAGMENT_TAGS]


def build_profiles(html: str, g: Graph) -> list[Profile]:
    profiles: list[Profile] = []
    instance_names = {str(s).split("#")[-1] for s in g.subjects() if str(s).startswith(NS)}

    for country, raw in sorted(js_object_flavors(html, "COUNTRY_DATA").items()):
        frags = country_fragments(raw)
        missing = unclassified_fragments(frags)
        if missing:
            raise ValueError(f"COUNTRY_DATA[{country}] unclassified: {missing}")
        if country not in instance_names:
            raise ValueError(f"COUNTRY_DATA key {country} has no RDF instance")
        tags = [t for f in frags for t in FRAGMENT_TAGS[f]]
        profiles.append(_apply(country, tags, f"COUNTRY_DATA.{country}.flavor"))

    harvests = js_object_flavors(html, "HARVEST_DATA")
    for region, raw in sorted(harvests.items()):
        frags = harvest_fragments(raw)
        missing = unclassified_fragments(frags)
        if missing:
            raise ValueError(f"HARVEST_DATA[{region}] unclassified: {missing}")
        tags = [t for f in frags for t in FRAGMENT_TAGS[f]]
        years = sorted(n for n in instance_names if re.fullmatch(rf"{region}_\d{{4}}", n))
        if not years:
            raise ValueError(f"HARVEST_DATA key {region} has no Harvest_<region>_<year> instance")
        for inst in years:
            profiles.append(_apply(inst, tags, f"HARVEST_DATA.{region}.flavor"))

    for subject, pairs in sorted(COMMENT_TAGS.items()):
        comment = g.value(COF[subject], RDFS.comment)
        if comment is None:
            raise ValueError(f"{subject} has no rdfs:comment")
        for _, snippet in pairs:
            if snippet not in str(comment):
                raise ValueError(f"{subject}: evidence '{snippet}' not in comment")
        profiles.append(_apply(subject, [t for t, _ in pairs], f"rdfs:comment of {subject}"))
    return profiles


# ── TTL rendering ───────────────────────────────────────────────────────

HEADER = """@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix cof:  <http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#> .

# ================================================================
# 커피랜드 온톨로지 — 2단계: 향미(Flavor)
# 자동 생성 파일 — 직접 고치지 말고 scripts/build_flavor_ttl.py 를 수정한 뒤
#   python scripts/build_flavor_ttl.py
# 로 다시 만드세요. (tests/test_flavor.py 가 최신 상태인지 검사합니다)
#
# 출처: dashboard.html 의 COUNTRY_DATA / HARVEST_DATA flavor 항목,
#       ProcessingMethod · RoastLevel · QualityGrade 의 rdfs:comment
# 분류 기준: SCA/WCR 커피 테이스터 향미 휠의 최상위 범주
# ================================================================

cof:FlavorNote a owl:Class ;
    rdfs:subClassOf cof:QualityAndProcessing ;
    rdfs:label "향미 노트"@ko , "Flavor Note"@en ;
    rdfs:comment "커피에서 느껴지는 개별 향미. SCA/WCR 향미 휠의 최상위 범주(hasFlavorCategory)로 분류한다."@ko .

cof:hasFlavorNote a owl:ObjectProperty ;
    rdfs:range cof:FlavorNote ;
    rdfs:label "향미 노트"@ko ;
    rdfs:comment "산지 국가·수확 지역·가공 방식·로스팅 단계·품질 등급이 가진 향미 노트."@ko .

cof:hasFlavorCategory a owl:DatatypeProperty ;
    rdfs:domain cof:FlavorNote ;
    rdfs:range xsd:string ;
    rdfs:comment "향미 휠 최상위 범주: Floral | Fruity | SourFermented | GreenVegetative | Roasted | Spices | NuttyCocoa | Sweet | Other"@ko .

cof:hasAcidityLevel a owl:DatatypeProperty ;
    rdfs:range xsd:string ;
    rdfs:comment "산미 강도: Low | Medium | High (원문 표현에서 분류)"@ko .

cof:hasBodyLevel a owl:DatatypeProperty ;
    rdfs:range xsd:string ;
    rdfs:comment "바디감: Light | Medium | Full (원문 표현에서 분류)"@ko .
"""


def _lit(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_ttl(profiles: list[Profile]) -> str:
    lines = [HEADER, "", "# ── 향미 노트 ──"]
    for note_id, (cat, ko, en) in NOTES.items():
        lines.append(
            f"cof:{note_id} a owl:NamedIndividual , cof:FlavorNote ;\n"
            f"    rdfs:label {_lit(ko)}@ko , {_lit(en)}@en ;\n"
            f"    cof:hasFlavorCategory {_lit(cat)}^^xsd:string ."
        )
    lines += ["", "# ── 향미 프로필 (출처별) ──"]
    for p in profiles:
        parts = []
        if p.notes:
            parts.append("cof:hasFlavorNote " + " , ".join(f"cof:{n}" for n in p.notes))
        if p.acidity:
            parts.append(f"cof:hasAcidityLevel {_lit(p.acidity)}^^xsd:string")
        if p.body:
            parts.append(f"cof:hasBodyLevel {_lit(p.body)}^^xsd:string")
        if not parts:
            continue
        lines.append(f"# {p.source}")
        lines.append(f"cof:{p.subject} " + " ;\n    ".join(parts) + " .")
    return "\n".join(lines) + "\n"


def build() -> str:
    with open(DASHBOARD, encoding="utf-8") as f:
        html = f.read()
    return render_ttl(build_profiles(html, load_rdf()))


def main(argv: list[str]) -> int:
    content = build()
    if "--check" in argv:
        with open(OUT_TTL, encoding="utf-8") as f:
            stale = f.read() != content
        if stale:
            sys.stderr.write("coffeeland_flavor.ttl is stale — run scripts/build_flavor_ttl.py\n")
        return 1 if stale else 0
    with open(OUT_TTL, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    sys.stdout.write(f"wrote {OUT_TTL}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
