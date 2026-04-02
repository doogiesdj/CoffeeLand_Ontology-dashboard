#!/usr/bin/env python3
"""
CoffeeLand RDF → JSON 변환 스크립트
RDF/TTL 파일을 읽어서 dashboard.html과 coffeeland-web이 사용하는 JSON을 생성합니다.
"""

import json
import os
import re
from collections import defaultdict
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RDF_FILE = os.path.join(BASE_DIR, 'data', 'coffeeland_final_v4.rdf')
TTL_FILE = os.path.join(BASE_DIR, 'data', 'coffeeland_data_enrichment.ttl')
OUT_DIR  = os.path.join(BASE_DIR, 'docs')
os.makedirs(OUT_DIR, exist_ok=True)

NS = "http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#"
COF = Namespace(NS)

def short(uri):
    if not uri: return ''
    uri = str(uri)
    h = uri.find('#')
    return uri[h+1:] if h >= 0 else uri.split('/')[-1]

# ── RDF 로드 ────────────────────────────────────────────────
print("📂 RDF 파일 로딩...")
g = Graph()
g.parse(RDF_FILE, format='xml')
print(f"   메인 RDF: {len(g)} 트리플")

if os.path.exists(TTL_FILE):
    g.parse(TTL_FILE, format='turtle')
    print(f"   TTL 보강: {len(g)} 트리플 (합계)")

total_triples = len(g)

# ── 클래스 파악 ─────────────────────────────────────────────
print("🏗  클래스 파악...")
all_classes = set()
for s in g.subjects(RDF.type, OWL.Class):
    name = short(s)
    if name and not name.startswith('_'):
        all_classes.add(name)

# 클래스 계층
subclass_map = defaultdict(list)  # parent → [children]
parent_map   = {}                  # child  → parent

for child, _, parent in g.triples((None, RDFS.subClassOf, None)):
    cn = short(child)
    pn = short(parent)
    if cn and pn and cn != pn:
        subclass_map[pn].append(cn)
        parent_map[cn] = pn

# 최상위 클래스 (부모 없는 것)
top_classes = [c for c in all_classes if c not in parent_map]

# ── 인스턴스 파악 ───────────────────────────────────────────
print("👤 인스턴스 파악...")
instances = {}
for s, _, cls in g.triples((None, RDF.type, None)):
    sn = short(s)
    cn = short(cls)
    if (cn in all_classes) and sn and not sn.startswith('_'):
        if sn not in instances:
            instances[sn] = {'types': [], 'obj': defaultdict(list), 'data': {}}
        if cn not in instances[sn]['types']:
            instances[sn]['types'].append(cn)

# 속성 수집
for s, p, o in g:
    sn = short(s)
    pn = short(p)
    if sn not in instances: continue
    if str(p).startswith(NS):
        on = short(o)
        if isinstance(o, URIRef):
            instances[sn]['obj'][pn].append(on)
        else:
            instances[sn]['data'][pn] = str(o)

# obj를 일반 dict로 변환
for k in instances:
    instances[k]['obj'] = dict(instances[k]['obj'])

# ── CO2 자동분류 ────────────────────────────────────────────
for name, inst in instances.items():
    if 'Farm' in inst['types']:
        co2 = float(inst['data'].get('hasCO2PerKg', 4.0))
        imp = inst['obj'].setdefault('hasImpact', [])
        if co2 > 6.0 and 'Metric_CO2_High' not in imp:
            imp.append('Metric_CO2_High')
        if co2 <= 3.0 and 'Metric_CO2_Low' not in imp:
            imp.append('Metric_CO2_Low')

# 럭셔리 브랜드 자동분류
for name, inst in instances.items():
    if 'CoffeeBrand' in inst['types']:
        price = float(inst['data'].get('hasPricePerKg', 0))
        if price >= 10.0:
            seg = inst['obj'].setdefault('hasPriceSegment', [])
            if 'PP_Luxury' not in seg:
                seg.append('PP_Luxury')

# ── 온톨로지 구조 JSON (dashboard.html용) ──────────────────
print("📊 온톨로지 구조 JSON 생성...")

def build_class_tree(cls_name):
    children = subclass_map.get(cls_name, [])
    inst_list = [n for n, i in instances.items() if cls_name in i['types']]
    return {
        'uri': NS + cls_name,
        'name': cls_name,
        'instanceCount': len(inst_list),
        'children': [build_class_tree(c) for c in sorted(children)],
        'instances': inst_list[:50]  # 최대 50개
    }

# ── Object Properties 추출 (Cytoscape 그래프용) ──────────────
from rdflib import RDFS as RDFS_LIB
obj_props = []
for s in g.subjects(RDF.type, OWL.ObjectProperty):
    name = short(s)
    if not name or name.startswith('_'):
        continue
    uri = str(s)
    domain = None
    for _, _, d in g.triples((s, RDFS_LIB.domain, None)):
        dn = short(d)
        if dn in all_classes:
            domain = NS + dn
            break
    ranges = []
    for _, _, r in g.triples((s, RDFS_LIB.range, None)):
        rn = short(r)
        if rn in all_classes:
            ranges.append(NS + rn)
    obj_props.append({'uri': uri, 'name': name, 'domain': domain, 'range': ranges})

# 클래스별 인스턴스 상세
instance_details = {}
for name, inst in instances.items():
    detail = {
        'uri': NS + name,
        'types': inst['types'],
        'properties': {}
    }
    # 데이터 속성
    for k, v in inst['data'].items():
        if k not in ['type']:
            detail['properties'][k] = {'type': 'data', 'value': v}
    # 객체 속성
    for k, vals in inst['obj'].items():
        if k not in ['type'] and vals:
            detail['properties'][k] = {'type': 'object', 'values': vals[:10]}
    instance_details[name] = detail

# 통계
stats_by_category = {}
category_map = {
    'Location': ['City','Country','Port','Warehouse','Region'],
    'Organization': ['CoffeeChain','Farm','Cooperative','Broker','Roaster',
                     'ImportBroker','LogisticsProvider','Retailer','ExportBroker'],
    'Market & Economics': ['PricePoint','MarketSegment','EconomicZone','TradingBloc'],
    'Product': ['CoffeeBrand','CoffeeVariety','ProcessingMethod','Certification'],
    'Quality & Processing': ['QualityGrade','SustainabilityMetric','Harvest']
}
for cat, cls_list in category_map.items():
    count = sum(len([n for n, i in instances.items() if c in i['types']]) for c in cls_list)
    stats_by_category[cat] = {
        'classes': len([c for c in cls_list if c in all_classes]),
        'instances': count
    }

ontology_json = {
    'meta': {
        'totalClasses': len(all_classes),
        'objectProperties': len(obj_props),
        'dataProperties': 20,
        'totalTriples': total_triples,
        'version': '2.0',
    },
    'classHierarchy': [build_class_tree(c) for c in sorted(top_classes)],
    'objectProperties': obj_props,
    'statsByCategory': stats_by_category,
    'instanceDetails': instance_details,
}

with open(os.path.join(OUT_DIR, 'ontology_data.json'), 'w', encoding='utf-8') as f:
    json.dump(ontology_json, f, ensure_ascii=False, indent=2)
print(f"   ontology_data.json 생성 완료 ({total_triples} 트리플)")

# ── 공급망 분석 JSON (coffeeland-web용) ─────────────────────
print("🌍 공급망 분석 JSON 생성...")

COORDS = {
    'Colombia':{'lat':4.5,'lng':-74.0},'Ethiopia':{'lat':9.0,'lng':38.7},
    'Kenya':{'lat':-1.3,'lng':36.8},'Indonesia':{'lat':-6.2,'lng':106.8},
    'Brazil':{'lat':-14.2,'lng':-51.9},'Costa_Rica':{'lat':9.7,'lng':-83.8},
    'Guatemala':{'lat':15.8,'lng':-90.2},'Peru':{'lat':-9.2,'lng':-75.0},
    'Honduras':{'lat':15.2,'lng':-86.2},'Tanzania':{'lat':-6.4,'lng':34.9},
    'Vietnam':{'lat':14.1,'lng':108.3},'Rwanda':{'lat':-2.0,'lng':29.9},
    'Nicaragua':{'lat':12.9,'lng':-85.2},'South_Korea':{'lat':37.6,'lng':127.0},
    'Japan':{'lat':35.7,'lng':139.7},'Singapore':{'lat':1.3,'lng':103.8},
    'Netherlands':{'lat':52.4,'lng':4.9},'USA':{'lat':37.1,'lng':-95.7},
    'Italy':{'lat':41.9,'lng':12.5},'Spain':{'lat':40.4,'lng':-3.7},
    'Germany':{'lat':51.2,'lng':10.5},'UK':{'lat':51.5,'lng':-0.1},
    'France':{'lat':46.2,'lng':2.2},'Australia':{'lat':-25.3,'lng':133.8},
    'Jamaica':{'lat':18.1,'lng':-77.3},'Panama':{'lat':8.5,'lng':-80.8},
    'Mexico':{'lat':23.6,'lng':-102.6},'Uganda':{'lat':1.4,'lng':32.3},
    'India':{'lat':20.6,'lng':78.9},'Yemen':{'lat':15.6,'lng':48.5},
    'El_Salvador':{'lat':13.8,'lng':-88.9},'Papua_New_Guinea':{'lat':-6.3,'lng':143.9},
    'Dominican_Republic':{'lat':18.7,'lng':-70.2},
}
PORT_COORDS = {
    'Port_Busan':{'lat':35.1,'lng':129.0,'label':'Busan'},
    'Port_Rotterdam':{'lat':51.9,'lng':4.5,'label':'Rotterdam'},
    'Port_Hamburg':{'lat':53.5,'lng':10.0,'label':'Hamburg'},
    'Port_Singapore':{'lat':1.26,'lng':103.8,'label':'Singapore'},
    'Port_Tokyo':{'lat':35.6,'lng':139.8,'label':'Tokyo'},
    'Port_Santos':{'lat':-23.9,'lng':-46.3,'label':'Santos'},
    'Port_Mombasa':{'lat':-4.1,'lng':39.7,'label':'Mombasa'},
    'Port_HoChiMinh':{'lat':10.8,'lng':106.7,'label':'Ho Chi Minh'},
    'Port_LongBeach':{'lat':33.8,'lng':-118.2,'label':'Long Beach'},
    'Port_NewOrleans':{'lat':29.9,'lng':-90.1,'label':'New Orleans'},
    'Port_Genoa':{'lat':44.4,'lng':8.9,'label':'Genoa'},
    'Port_Valencia':{'lat':39.5,'lng':-0.3,'label':'Valencia'},
    'Port_Sydney':{'lat':-33.9,'lng':151.2,'label':'Sydney'},
    'Port_Felixstowe':{'lat':51.9,'lng':1.3,'label':'Felixstowe'},
    'Port_Antwerp':{'lat':51.2,'lng':4.4,'label':'Antwerp'},
    'Port_Buenaventura':{'lat':3.9,'lng':-77.0,'label':'Buenaventura'},
    'Port_Callao':{'lat':-12.1,'lng':-77.1,'label':'Callao'},
    'Port_PuertoBarrios':{'lat':15.7,'lng':-88.6,'label':'Puerto Barrios'},
    'Port_PuertoCortes':{'lat':15.8,'lng':-87.9,'label':'Puerto Cortés'},
    'Port_PuertoLimon':{'lat':10.0,'lng':-83.0,'label':'Puerto Limón'},
    'Port_Surabaya':{'lat':-7.2,'lng':112.7,'label':'Surabaya'},
    'Port_Mumbai':{'lat':19.0,'lng':72.8,'label':'Mumbai'},
    'Port_LeHavre':{'lat':49.5,'lng':0.1,'label':'Le Havre'},
    'Port_Trieste':{'lat':45.6,'lng':13.8,'label':'Trieste'},
    'Port_NewYork':{'lat':40.7,'lng':-74.0,'label':'New York'},
    'Port_Shanghai':{'lat':31.2,'lng':121.5,'label':'Shanghai'},
    'Port_Guangzhou':{'lat':22.6,'lng':113.6,'label':'Guangzhou'},
    'Port_Vancouver':{'lat':49.3,'lng':-123.1,'label':'Vancouver'},
    'Port_Montreal':{'lat':45.5,'lng':-73.6,'label':'Montreal'},
    'Port_SaintPetersburg':{'lat':59.9,'lng':30.3,'label':'Saint Petersburg'},
    'Port_Gdansk':{'lat':54.4,'lng':18.7,'label':'Gdansk'},
    'Port_Algiers':{'lat':36.8,'lng':3.1,'label':'Algiers'},
    'Port_Istanbul':{'lat':41.0,'lng':28.7,'label':'Istanbul'},
    'Port_Gothenburg':{'lat':57.7,'lng':11.9,'label':'Gothenburg'},
    'Port_Helsinki':{'lat':60.2,'lng':25.2,'label':'Helsinki'},
    'Port_Jeddah':{'lat':21.5,'lng':39.2,'label':'Jeddah'},
    'Port_Vienna':{'lat':48.2,'lng':16.4,'label':'Vienna'},
    'Port_Prague':{'lat':50.1,'lng':14.4,'label':'Prague'},
    'Port_Oslo':{'lat':59.9,'lng':10.8,'label':'Oslo'},
    'Port_Piraeus':{'lat':37.9,'lng':23.6,'label':'Piraeus'},
}
WAREHOUSE_COORDS = {
    # Consumer country warehouses
    'Warehouse_Seattle_Port':{'lat':47.6,'lng':-122.3},
    'Warehouse_Busan_Port':{'lat':35.1,'lng':129.1},
    'Warehouse_Amsterdam_West':{'lat':52.4,'lng':4.8},
    'Warehouse_LongBeach_South':{'lat':33.8,'lng':-118.2},
    'Warehouse_Genoa_Harbor':{'lat':44.4,'lng':8.9},
    'Warehouse_Sydney_South':{'lat':-33.9,'lng':151.2},
    'Warehouse_Hamburg_Central':{'lat':53.5,'lng':10.0},
    'Warehouse_Tokyo_Bay':{'lat':35.6,'lng':139.8},
    'Warehouse_Barcelona_Port':{'lat':41.4,'lng':2.2},
    'Warehouse_Antwerp_North':{'lat':51.3,'lng':4.4},
    'Warehouse_Rotterdam_West':{'lat':51.9,'lng':4.5},
    'Warehouse_Miami_FreeZone':{'lat':25.8,'lng':-80.2},
    'Warehouse_Melbourne_Docks':{'lat':-37.8,'lng':144.9},
    'Warehouse_NewOrleans_CBD':{'lat':30.0,'lng':-90.1},
    'Warehouse_Felixstowe_East':{'lat':51.9,'lng':1.3},
    'Warehouse_Valencia_Industrial':{'lat':39.5,'lng':-0.4},
    'Warehouse_Singapore_West':{'lat':1.3,'lng':103.7},
    # Producer country warehouses
    'Warehouse_Santos_A':{'lat':-23.9,'lng':-46.3},
    'Warehouse_HoChiMinh_District7':{'lat':10.7,'lng':106.7},
    'Warehouse_Mombasa_Central':{'lat':-4.0,'lng':39.7},
    'Warehouse_Buenaventura':{'lat':3.9,'lng':-77.1},
    'Warehouse_PuertoBarrios':{'lat':15.7,'lng':-88.6},
    'Warehouse_PuertoCortes':{'lat':15.8,'lng':-88.0},
    'Warehouse_PuertoLimon':{'lat':10.0,'lng':-83.1},
    'Warehouse_Callao':{'lat':-12.1,'lng':-77.2},
    'Warehouse_Surabaya':{'lat':-7.3,'lng':112.7},
    'Warehouse_Addis_Ababa':{'lat':9.0,'lng':38.7},
    'Warehouse_Mumbai':{'lat':19.1,'lng':72.9},
    'Warehouse_Kigali':{'lat':-1.9,'lng':30.1},
    'Warehouse_Dar_es_Salaam':{'lat':-6.8,'lng':39.3},
    'Warehouse_Kampala':{'lat':0.3,'lng':32.6},
    'Warehouse_Veracruz':{'lat':19.2,'lng':-96.1},
    'Warehouse_Managua':{'lat':12.1,'lng':-86.3},
    'Warehouse_Kingston':{'lat':18.0,'lng':-76.8},
    'Warehouse_Sanaa':{'lat':15.4,'lng':44.2},
    # New consumer country warehouses
    'Warehouse_Shanghai':{'lat':31.4,'lng':121.6},
    'Warehouse_Guangzhou':{'lat':22.6,'lng':113.6},
    'Warehouse_Vancouver':{'lat':49.3,'lng':-123.0},
    'Warehouse_Montreal':{'lat':45.5,'lng':-73.5},
    'Warehouse_SaintPetersburg':{'lat':59.8,'lng':29.8},
    'Warehouse_Gdansk':{'lat':54.4,'lng':18.7},
    'Warehouse_Algiers':{'lat':36.8,'lng':3.1},
    'Warehouse_Istanbul':{'lat':41.0,'lng':28.7},
    'Warehouse_Gothenburg':{'lat':57.7,'lng':12.0},
    'Warehouse_Helsinki':{'lat':60.2,'lng':25.2},
    'Warehouse_Jeddah':{'lat':21.5,'lng':39.2},
    'Warehouse_Vienna':{'lat':48.2,'lng':16.5},
    'Warehouse_Prague':{'lat':50.0,'lng':14.6},
    'Warehouse_Oslo':{'lat':59.9,'lng':10.9},
    'Warehouse_Piraeus':{'lat':38.0,'lng':23.6},
}

# Actual farm coordinates (real locations)
FARM_COORDS = {
    # Brazil
    'Farm_Minas_Gerais_Fazenda_Sertao':{'lat':-21.2,'lng':-45.0},
    'Farm_Sao_Paulo_Fazenda_Ipe':{'lat':-22.8,'lng':-49.2},
    'Farm_Espirito_Santo_Fazenda_Santa_Rita':{'lat':-20.3,'lng':-41.5},
    'Farm_Cerrado_Fazenda_Dutra':{'lat':-18.9,'lng':-47.5},
    # Colombia
    'Farm_Huila_El_Paraiso_Farm':{'lat':2.0,'lng':-76.0},
    'Farm_Narino_San_Juan_Farm':{'lat':1.3,'lng':-77.5},
    'Farm_Antioquia_La_Esperanza':{'lat':6.2,'lng':-75.6},
    # Ethiopia
    'Farm_Yirgacheffe_Kochere_Farm':{'lat':6.2,'lng':38.2},
    'Farm_Sidamo_Guji_Farm':{'lat':5.8,'lng':38.5},
    'Farm_Harrar_Estate':{'lat':9.3,'lng':42.1},
    # Kenya
    'Farm_Nyeri_Gatomboya_Farm':{'lat':-0.4,'lng':36.9},
    'Farm_Kiambu_Kagumo_Estate':{'lat':-1.2,'lng':36.8},
    # Indonesia
    'Farm_Java_Ijen_Estate':{'lat':-8.1,'lng':114.2},
    'Farm_Sumatra_Mandheling_Gayo_Farm':{'lat':4.6,'lng':96.8},
    'Farm_Sulawesi_Toraja_Estate':{'lat':-3.0,'lng':119.9},
    # Guatemala
    'Farm_Antigua_Finca_El_Injerto':{'lat':14.6,'lng':-90.7},
    'Farm_Huehuetenango_Finca_Vista_Hermosa':{'lat':15.3,'lng':-91.5},
    # Honduras
    'Farm_Copan_San_Marcos_Farm':{'lat':14.8,'lng':-88.8},
    'Farm_Marcala_Highland_Estate':{'lat':14.2,'lng':-88.0},
    # Costa Rica
    'Farm_Tarrazu_La_Minita_Farm':{'lat':9.6,'lng':-84.0},
    'Farm_West_Valley_Helsar_Farm':{'lat':10.1,'lng':-84.4},
    # Vietnam
    'Farm_Dak_Lak_Central_Highlands_Farm':{'lat':12.7,'lng':108.0},
    'Farm_Lam_Dong_Arabica_Farm':{'lat':11.9,'lng':108.4},
    # Peru
    'Farm_Cajamarca_Villa_Rica_Farm':{'lat':-10.7,'lng':-75.3},
    # India
    'Farm_Malabar_Coast_Estate':{'lat':11.5,'lng':76.0},
    # Rwanda
    'Farm_Western_Province_Huye_Mountain':{'lat':-2.5,'lng':29.5},
    'Farm_Huye_Mountain_Estate':{'lat':-2.6,'lng':29.6},
    # Tanzania
    'Farm_Kilimanjaro_Moshi_Estate':{'lat':-3.3,'lng':37.3},
    # Uganda
    'Farm_Bugisu_Sipi_Falls':{'lat':1.3,'lng':34.3},
    # Mexico
    'Farm_Chiapas_Finca_Irlanda':{'lat':15.4,'lng':-92.3},
    # Nicaragua
    'Farm_Jinotega_Finca_Mierisch':{'lat':13.1,'lng':-86.0},
    # Panama
    'Farm_Boquete_Hacienda_Esmeralda':{'lat':8.8,'lng':-82.4},
    # Jamaica
    'Farm_Blue_Mountain_Estate':{'lat':18.1,'lng':-76.6},
    # El Salvador
    'Farm_Santa_Ana_Los_Pirineos':{'lat':13.9,'lng':-89.6},
    # Dominican Republic
    'Farm_Barahona_La_Montana':{'lat':18.2,'lng':-71.1},
    # Papua New Guinea
    'Farm_Highlands_Sigri_Estate':{'lat':-5.9,'lng':144.0},
    # USA (Hawaii Kona)
    'Farm_Kona_Greenwell':{'lat':19.5,'lng':-155.9},
    # Yemen
    'Farm_Sanani_Bani_Matar':{'lat':15.2,'lng':44.0},
}

# 농장 지도 데이터
farm_map = []
for name, inst in instances.items():
    if 'Farm' not in inst['types']: continue
    countries = inst['obj'].get('isLocatedIn', [])
    brands = inst['obj'].get('producedFor', [])
    co2 = float(inst['data'].get('hasCO2PerKg', 4.0))
    impacts = inst['obj'].get('hasImpact', [])
    esg = 'low' if 'Metric_CO2_Low' in impacts else ('high' if 'Metric_CO2_High' in impacts else 'mid')
    for c in countries:
        if c in COORDS:
            fc = FARM_COORDS.get(name)
            if fc:
                flat, flng = fc['lat'], fc['lng']
            else:
                flat = COORDS[c]['lat'] + (hash(name)%10-5)*.3
                flng = COORDS[c]['lng'] + (hash(name)%7-3)*.3
            farm_map.append({
                'name': name.replace('Farm_','').replace('_',' '),
                'id': name, 'lat': flat, 'lng': flng,
                'country': c.replace('_',' '), 'brands': brands, 'co2': co2, 'esg': esg
            })

port_map = [{'id':k,'lat':v['lat'],'lng':v['lng'],'label':v['label']} for k,v in PORT_COORDS.items()]

# 브랜드 데이터
brands_list = []
for name, inst in instances.items():
    if 'CoffeeBrand' not in inst['types']: continue
    price = float(inst['data'].get('hasPricePerKg', 0))
    method = (inst['obj'].get('usesMethod',[''])[0]).replace('_Process','').replace('_',' ')
    seg = inst['obj'].get('hasPriceSegment',[''])[0].replace('PP_','')
    # 가격이 없으면 PriceSegment 기반으로 현실적 가격 할당
    if price == 0 and seg:
        import random; random.seed(hash(name))
        seg_prices = {
            'Luxury': (12.0, 18.0), 'Specialty': (9.5, 12.0),
            'Premium': (8.0, 10.5), 'MidRange': (6.0, 8.0), 'Budget': (3.5, 6.0)
        }
        lo, hi = seg_prices.get(seg, (5.0, 8.0))
        price = round(lo + random.random() * (hi - lo), 1)
    certs = inst['obj'].get('brandHasCertification', [])
    impacts = inst['obj'].get('hasBrandImpact', [])
    farms = inst['obj'].get('sourcedFrom', [])
    co2s = inst['obj'].get('hasBrandImpact', [])
    co2_score = 10 if 'Metric_CO2_Low' in co2s else (2 if 'Metric_CO2_High' in co2s else 6)
    brands_list.append({
        'name': name.replace('_',' '), 'id': name, 'price': price,
        'method': method or '—', 'segment': seg or '—', 'certs': certs,
        'esg': {'co2': co2_score,
                'fairTrade': 9 if 'Fair_Trade' in certs else 3,
                'organic': 9 if 'Organic' in certs else 4,
                'rainforest': 8 if 'Rainforest_Alliance' in certs else 4,
                'water': 7},
        'farms': [f.replace('Farm_','').replace('_',' ') for f in farms],
        'impacts': impacts
    })
brands_list.sort(key=lambda x: -x['price'])

# 원두 추적
trace = []
for menu_name, menu in instances.items():
    if 'BeverageMenu' not in menu['types']: continue
    for brand_name in menu['obj'].get('usesCoffeeBrand', []):
        for farm_name, farm in instances.items():
            if 'Farm' not in farm['types']: continue
            if brand_name in farm['obj'].get('producedFor', []):
                for country in farm['obj'].get('isLocatedIn', []):
                    trace.append({'menu':menu_name,'brand':brand_name,
                                  'farm':farm_name,'country':country})

# ESG
esg_high = []
for farm_name, farm in instances.items():
    if 'Farm' not in farm['types']: continue
    if 'Metric_CO2_High' in farm['obj'].get('hasImpact', []):
        for brand in farm['obj'].get('producedFor', []):
            for chain in instances.get(brand,{}).get('obj',{}).get('usesByChain',[]):
                esg_high.append({'farm':farm_name.replace('Farm_','').replace('_',' '),
                                 'brand':brand.replace('_',' '),'chain':chain.replace('_',' '),
                                 'co2':farm['data'].get('hasCO2PerKg','')})

esg_good = []
for name, inst in instances.items():
    if 'CoffeeBrand' not in inst['types']: continue
    certs = inst['obj'].get('brandHasCertification', [])
    if 'Fair_Trade' in certs and 'Organic' in certs:
        esg_good.append({'name':name.replace('_',' '),'certs':certs})

# 공급망
supply_coop  = [{'farm':n.replace('Farm_','').replace('_',' '),'coop':c}
                for n,i in instances.items() if 'Farm' in i['types']
                for c in i['obj'].get('memberOfCoop',[])]
supply_port  = [{'warehouse':n,'port':p}
                for n,i in instances.items() if 'Warehouse' in i['types']
                for p in i['obj'].get('adjacentTo',[])]
supply_chain = [{'brand':n.replace('_',' '),'chain':c.replace('_',' ')}
                for n,i in instances.items() if 'CoffeeBrand' in i['types']
                for c in i['obj'].get('usesByChain',[])]

# 흐름도 노드/링크
flow_nodes, flow_links, node_ids = [], [], set()
for name, inst in instances.items():
    if 'Farm' in inst['types']:
        nid = 'farm_'+name
        if nid not in node_ids:
            co2 = float(inst['data'].get('hasCO2PerKg',4.0))
            flow_nodes.append({'id':nid,'label':name.replace('Farm_','').replace('_',' '),'type':'farm','co2':co2})
            node_ids.add(nid)
        for brand in inst['obj'].get('producedFor',[]):
            bid = 'brand_'+brand
            if bid not in node_ids:
                p = float(instances.get(brand,{}).get('data',{}).get('hasPricePerKg',0))
                flow_nodes.append({'id':bid,'label':brand.replace('_',' '),'type':'brand','price':p})
                node_ids.add(bid)
            flow_links.append({'source':nid,'target':bid,'type':'produces'})

for name, inst in instances.items():
    if 'CoffeeBrand' in inst['types']:
        bid = 'brand_'+name
        for chain in inst['obj'].get('usesByChain',[]):
            cid = 'chain_'+chain
            if cid not in node_ids:
                flow_nodes.append({'id':cid,'label':chain.replace('_',' '),'type':'chain'})
                node_ids.add(cid)
            flow_links.append({'source':bid,'target':cid,'type':'supplies'})

# 공급망 흐름도에 필요한 엔티티 목록 (coffeeland-web renderTraceFlow용)
consumer_countries = {'USA','South_Korea','Japan','UK','Australia','Canada','China','Italy','Germany','France','Spain','Netherlands','Belgium','Singapore','Denmark','Taiwan','Switzerland','Russia','Poland','Algeria','Turkey','Sweden','Finland','Saudi_Arabia','Austria','Czech_Republic','Norway','Greece'}

# 창고: country, port(adjacentTo) 포함
consumer_warehouses = []
producer_warehouses = []
for n,i in instances.items():
    if 'Warehouse' not in i['types']: continue
    countries = i['obj'].get('isLocatedIn',[])
    ports = i['obj'].get('adjacentTo',[])
    wh = {'id':n,'label':n.replace('Warehouse_','').replace('_',' '),
          'country':countries[0].replace('_',' ') if countries else '',
          'port':ports[0] if ports else ''}
    if any(c in consumer_countries for c in countries):
        consumer_warehouses.append(wh)
    else:
        producer_warehouses.append(wh)

# Import Broker: brands(mediates), hq(isHeadquarteredIn), cw(연결된 소비국 창고), cp(연결된 소비국 항구)
import_brokers = []
for n,i in instances.items():
    if 'ImportBroker' not in i['types']: continue
    hqs = i['obj'].get('isHeadquarteredIn',[])
    brands = i['obj'].get('mediates',[])
    # 해당 브로커가 구매하는 농장들이 연결된 창고/항구 매핑
    cws = [w['id'] for w in consumer_warehouses]  # 모든 소비국 창고 연결
    cps = [p for p in i['obj'].get('transportsTo',[])] or []
    import_brokers.append({'id':n,'label':n.replace('_',' '),
                           'hq':hqs[0].replace('_',' ') if hqs else '',
                           'brands':brands,
                           'warehouses':cws[:3],  # 상위 3개
                           'ports':cps})

# Export Broker: brands(mediates), hq, ports(연결된 생산국 항구)
export_brokers = []
for n,i in instances.items():
    if 'ExportBroker' not in i['types']: continue
    hqs = i['obj'].get('isHeadquarteredIn',[])
    brands = i['obj'].get('mediates',[])
    farms = i['obj'].get('purchasesFrom',[])
    # 생산국 항구 연결: 농장이 위치한 국가 근처 항구
    farm_countries = set()
    for f in farms:
        if f in instances:
            for c in instances[f]['obj'].get('isLocatedIn',[]):
                farm_countries.add(c)
    pp_ids = [p['id'] for p in producer_ports] if 'producer_ports' in dir() else []
    export_brokers.append({'id':n,'label':n.replace('_',' '),
                           'hq':hqs[0].replace('_',' ') if hqs else '',
                           'brands':brands,
                           'ports':[]})  # 아래에서 채움

# Logistics Provider: from(transportsFrom), to(transportsTo), hq
logistics_providers = []
for n,i in instances.items():
    if 'LogisticsProvider' not in i['types']: continue
    hqs = i['obj'].get('isHeadquarteredIn',[])
    froms = i['obj'].get('transportsFrom',[])
    tos = i['obj'].get('transportsTo',[])
    logistics_providers.append({'id':n,'label':n.replace('_',' '),
                                'hq':hqs[0].replace('_',' ') if hqs else '',
                                'from':froms,'to':tos})

# 소비국/생산국 항구 분류
consumer_ports = []
producer_ports = []
for n,i in instances.items():
    if 'Port' not in i['types']: continue
    countries = i['obj'].get('isLocatedIn',[])
    port = {'id':n,'label':n.replace('Port_','').replace('_',' '),
            'country':countries[0].replace('_',' ') if countries else ''}
    if any(c in consumer_countries for c in countries):
        consumer_ports.append(port)
    else:
        producer_ports.append(port)
# 분류 안 된 항구는 producer
all_port_ids = set(p['id'] for p in consumer_ports + producer_ports)
for n,i in instances.items():
    if 'Port' in i['types'] and n not in all_port_ids:
        producer_ports.append({'id':n,'label':n.replace('Port_','').replace('_',' '),'country':''})

# Add coordinates to ports from PORT_COORDS
for p_list in [consumer_ports, producer_ports]:
    for p in p_list:
        coords = PORT_COORDS.get(p['id'])
        if coords:
            p['lat'] = coords['lat']
            p['lng'] = coords['lng']

# Add coordinates to warehouses from WAREHOUSE_COORDS
for w_list in [consumer_warehouses, producer_warehouses]:
    for w in w_list:
        coords = WAREHOUSE_COORDS.get(w['id'])
        if coords:
            w['lat'] = coords['lat']
            w['lng'] = coords['lng']

# Export Broker ports 채우기
pp_ids = [p['id'] for p in producer_ports]
for eb in export_brokers:
    eb['ports'] = pp_ids[:3]  # 생산국 항구들과 연결

# 국가별 수출 항구 매핑 (renderTraceFlow의 farm_export_port)
farm_export_port = {
    'Colombia':'Port_Buenaventura','Brazil':'Port_Santos','Ethiopia':'Port_Mombasa',
    'USA':'Port_LongBeach',
    'Kenya':'Port_Mombasa','Indonesia':'Port_Surabaya','Guatemala':'Port_PuertoBarrios',
    'Honduras':'Port_PuertoCortes','Costa Rica':'Port_PuertoLimon','Peru':'Port_Callao',
    'Vietnam':'Port_HoChiMinh','Jamaica':'Port_Santos','Panama':'Port_Buenaventura',
    'Mexico':'Port_HoChiMinh','Rwanda':'Port_Mombasa','Tanzania':'Port_Mombasa',
    'Uganda':'Port_Mombasa','India':'Port_Mumbai','Yemen':'Port_Mumbai',
    'Nicaragua':'Port_PuertoCortes','El Salvador':'Port_PuertoBarrios',
    'Papua New Guinea':'Port_Surabaya','Dominican Republic':'Port_Santos',
}

# ── trace_flow_links: 11-column supply chain links (RDF-driven) ──
# Prefixes: m_(menu), b_(brand), cw_(consumer warehouse), ib_(import broker),
#           cp_(consumer port), lp_(logistics), pp_(producer port),
#           eb_(export broker), pw_(producer warehouse), f_(farm), co_(country)
print("🔗 trace_flow_links 생성...")
trace_flow_links = []
tfl_set = set()

def add_tfl(src, tgt):
    key = src + '|' + tgt
    if key not in tfl_set:
        tfl_set.add(key)
        trace_flow_links.append({'source': src, 'target': tgt})

# 1. Menu → Brand (from trace data)
for t in trace:
    add_tfl('m_' + t['menu'], 'b_' + t['brand'])

# 2. Brand → CW: brand uses chains → chains operate in cities/countries → warehouses in those countries
#    Indirect: link brands to consumer warehouses via the import brokers that mediate them
brand_to_ibs = defaultdict(list)
for ib in import_brokers:
    for b in ib['brands']:
        brand_to_ibs[b].append(ib['id'])

# Build IB → CW links based on warehouse adjacentTo ports + IB HQ geography
ib_to_cws = defaultdict(list)
ib_to_cps = defaultdict(list)

# Map each IB to warehouses: IB HQ country → find warehouses in same region
# Use port adjacency: warehouse.adjacentTo → port, IB transportsTo → same ports
for ib_data in import_brokers:
    ib_id = ib_data['id']
    ib_inst = instances.get(ib_id, {})
    ib_hqs = ib_inst.get('obj', {}).get('isHeadquarteredIn', [])
    ib_ports = ib_inst.get('obj', {}).get('transportsTo', [])

    # Link IB to consumer warehouses whose adjacentTo port matches IB's ports
    matched_cws = set()
    matched_cps = set()
    for cw in consumer_warehouses:
        cw_inst = instances.get(cw['id'], {})
        cw_ports = cw_inst.get('obj', {}).get('adjacentTo', [])
        # If IB has specific ports, match; otherwise link to all CWs
        if ib_ports:
            if any(p in ib_ports for p in cw_ports):
                matched_cws.add(cw['id'])
                for p in cw_ports:
                    if p in ib_ports:
                        matched_cps.add(p)
        else:
            # No specific ports → link to all consumer warehouses (IB is intermediary)
            matched_cws.add(cw['id'])
            for p in cw_ports:
                matched_cps.add(p)

    # If no matches found, link to all consumer warehouses (fallback)
    if not matched_cws:
        for cw in consumer_warehouses:
            matched_cws.add(cw['id'])
    if not matched_cps:
        for cp in consumer_ports:
            matched_cps.add(cp['id'])

    ib_to_cws[ib_id] = list(matched_cws)
    ib_to_cps[ib_id] = list(matched_cps)

# Now build Brand → CW links via IB
for brand_name in [b['id'] for b in brands_list]:
    ibs = brand_to_ibs.get(brand_name, [])
    cw_set = set()
    for ib_id in ibs:
        for cw_id in ib_to_cws.get(ib_id, []):
            cw_set.add(cw_id)
    # Fallback: brands with no IB get linked to all consumer warehouses
    if not cw_set:
        cw_set = set(cw['id'] for cw in consumer_warehouses[:3])
    for cw_id in cw_set:
        add_tfl('b_' + brand_name, 'cw_' + cw_id)

# 3. CW → IB: warehouse adjacentTo port, IB operates through same ports
for ib_data in import_brokers:
    ib_id = ib_data['id']
    for cw_id in ib_to_cws.get(ib_id, []):
        add_tfl('cw_' + cw_id, 'ib_' + ib_id)

# 4. IB → CP: import broker linked to consumer ports
# Also ensure all consumer ports have incoming links
all_cp_ids = set(cp['id'] for cp in consumer_ports)
linked_cps = set()
for ib_data in import_brokers:
    ib_id = ib_data['id']
    for cp_id in ib_to_cps.get(ib_id, []):
        add_tfl('ib_' + ib_id, 'cp_' + cp_id)
        linked_cps.add(cp_id)
# Fallback: unlinked consumer ports get connected to all import brokers
for cp_id in all_cp_ids - linked_cps:
    for ib_data in import_brokers[:3]:
        add_tfl('ib_' + ib_data['id'], 'cp_' + cp_id)

# 5. CP → LP: logistics_provider.transportsTo matches consumer ports
for lp in logistics_providers:
    for cp_id in lp['to']:
        add_tfl('cp_' + cp_id, 'lp_' + lp['id'])

# 6. LP → PP: logistics_provider.transportsFrom matches producer ports
all_pp_ids = set(pp['id'] for pp in producer_ports)
linked_pps_in = set()
for lp in logistics_providers:
    for pp_id in lp['from']:
        add_tfl('lp_' + lp['id'], 'pp_' + pp_id)
        linked_pps_in.add(pp_id)
# Fallback: unlinked producer ports get connected to nearest logistics providers
for pp_id in all_pp_ids - linked_pps_in:
    for lp in logistics_providers[:2]:
        add_tfl('lp_' + lp['id'], 'pp_' + pp_id)

# Build port-to-warehouse and country-to-port/warehouse lookups
pp_to_pw = {}
country_to_pw = {}
for pw in producer_warehouses:
    pw_inst = instances.get(pw['id'], {})
    pw_ports = pw_inst.get('obj', {}).get('adjacentTo', [])
    pw_countries = pw_inst.get('obj', {}).get('isLocatedIn', [])
    for p in pw_ports:
        pp_to_pw[p] = pw['id']
    for c in pw_countries:
        country_to_pw[c] = pw['id']

# 7. PP → EB: export broker connected via farms they purchase from
for eb_name, eb_inst in instances.items():
    if 'ExportBroker' not in eb_inst.get('types', []): continue
    eb_farms = eb_inst.get('obj', {}).get('purchasesFrom', [])
    eb_ports_set = set()
    for farm_name in eb_farms:
        farm_inst = instances.get(farm_name, {})
        for fc in farm_inst.get('obj', {}).get('isLocatedIn', []):
            ep = farm_export_port.get(fc, farm_export_port.get(fc.replace('_', ' '), ''))
            if ep:
                eb_ports_set.add(ep)
    # Also add explicit ports from eb data
    eb_data = next((e for e in export_brokers if e['id'] == eb_name), None)
    if eb_data:
        for p in eb_data.get('ports', []):
            eb_ports_set.add(p)
    # Fallback: EB with no ports gets connected to first 2 producer ports
    if not eb_ports_set:
        for pp in producer_ports[:2]:
            eb_ports_set.add(pp['id'])
    for pp_id in eb_ports_set:
        add_tfl('pp_' + pp_id, 'eb_' + eb_name)

# 8. EB → PW: via the same ports/countries
for eb_name, eb_inst in instances.items():
    if 'ExportBroker' not in eb_inst.get('types', []): continue
    eb_farms = eb_inst.get('obj', {}).get('purchasesFrom', [])
    for farm_name in eb_farms:
        farm_inst = instances.get(farm_name, {})
        for fc in farm_inst.get('obj', {}).get('isLocatedIn', []):
            pw_id = country_to_pw.get(fc)
            if pw_id:
                add_tfl('eb_' + eb_name, 'pw_' + pw_id)
            ep = farm_export_port.get(fc, farm_export_port.get(fc.replace('_', ' '), ''))
            if ep and ep in pp_to_pw:
                add_tfl('eb_' + eb_name, 'pw_' + pp_to_pw[ep])

# Fallback: ensure all producer warehouses have EB incoming and farm outgoing
all_pw_ids = set(pw['id'] for pw in producer_warehouses)
linked_pw_in = set(l['target'].replace('pw_','') for l in trace_flow_links if l['target'].startswith('pw_'))
linked_pw_out = set(l['source'].replace('pw_','') for l in trace_flow_links if l['source'].startswith('pw_'))
eb_list = [n for n,i in instances.items() if 'ExportBroker' in i.get('types',[])]
for pw_id in all_pw_ids - linked_pw_in:
    if eb_list:
        add_tfl('eb_' + eb_list[0], 'pw_' + pw_id)
for pw_id in all_pw_ids - linked_pw_out:
    pw_inst = instances.get(pw_id, {})
    pw_countries = pw_inst.get('obj', {}).get('isLocatedIn', [])
    for f in farm_map:
        if f['country'].replace(' ', '_') in pw_countries:
            add_tfl('pw_' + pw_id, 'f_' + f['id'])
            break

# Ensure all producer ports have EB outgoing
linked_pp_out = set(l['source'].replace('pp_','') for l in trace_flow_links if l['source'].startswith('pp_'))
for pp_id in all_pp_ids - linked_pp_out:
    if eb_list:
        add_tfl('pp_' + pp_id, 'eb_' + eb_list[0])

# 9. PW → Farm: farm isLocatedIn country, warehouse isLocatedIn same country
for f in farm_map:
    country = f['country'].replace(' ', '_')
    # Direct country match
    pw_id = country_to_pw.get(country)
    if pw_id:
        add_tfl('pw_' + pw_id, 'f_' + f['id'])
    # Also via export port
    ep = farm_export_port.get(f['country'])
    if ep:
        pw_id2 = pp_to_pw.get(ep)
        if pw_id2:
            add_tfl('pw_' + pw_id2, 'f_' + f['id'])

# 10. Farm → Country
for f in farm_map:
    add_tfl('f_' + f['id'], 'co_' + f['country'].replace(' ', '_'))

print(f"   trace_flow_links: {len(trace_flow_links)} 링크 생성")

supply_json = {
    'stats': {
        'menus': len([n for n,i in instances.items() if 'BeverageMenu' in i['types']]),
        'brands': len(brands_list),
        'farms': len([n for n,i in instances.items() if 'Farm' in i['types']]),
        'countries': len([n for n,i in instances.items() if 'Country' in i['types']]),
        'chains': len([n for n,i in instances.items() if 'CoffeeChain' in i['types']]),
        'ports': len(port_map),
        'triples': total_triples,
    },
    'farm_map': farm_map, 'port_map': port_map,
    'brands': brands_list, 'trace': trace,
    'esg_high': esg_high, 'esg_good': esg_good,
    'supply_coop': supply_coop, 'supply_port': supply_port, 'supply_chain': supply_chain,
    'flow_nodes': flow_nodes, 'flow_links': flow_links,
    'consumer_warehouses': consumer_warehouses,
    'producer_warehouses': producer_warehouses,
    'import_brokers': import_brokers,
    'export_brokers': export_brokers,
    'logistics_providers': logistics_providers,
    'consumer_ports': consumer_ports,
    'producer_ports': producer_ports,
    'farm_export_port': farm_export_port,
    'trace_flow_links': trace_flow_links,
}

with open(os.path.join(OUT_DIR, 'coffeeland_data.json'), 'w', encoding='utf-8') as f:
    json.dump(supply_json, f, ensure_ascii=False, indent=2)
print(f"   coffeeland_data.json 생성 완료 (브랜드 {len(brands_list)}개, 추적 {len(trace)}건)")

print("\n✅ 모든 JSON 생성 완료!")
print(f"   - docs/ontology_data.json  (dashboard.html용)")
print(f"   - docs/coffeeland_data.json (coffeeland-web용)")
