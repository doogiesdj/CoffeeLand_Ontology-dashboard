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
            farm_map.append({
                'name': name.replace('Farm_','').replace('_',' '),
                'id': name, 'lat': COORDS[c]['lat'] + (hash(name)%10-5)*.3,
                'lng': COORDS[c]['lng'] + (hash(name)%7-3)*.3,
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
consumer_countries = {'USA','South_Korea','Japan','UK','Australia','Canada','China','Italy','Germany','France','Spain','Netherlands'}

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
    for cw_id in cw_set:
        add_tfl('b_' + brand_name, 'cw_' + cw_id)

# 3. CW → IB: warehouse adjacentTo port, IB operates through same ports
for ib_data in import_brokers:
    ib_id = ib_data['id']
    for cw_id in ib_to_cws.get(ib_id, []):
        add_tfl('cw_' + cw_id, 'ib_' + ib_id)

# 4. IB → CP: import broker linked to consumer ports
for ib_data in import_brokers:
    ib_id = ib_data['id']
    for cp_id in ib_to_cps.get(ib_id, []):
        add_tfl('ib_' + ib_id, 'cp_' + cp_id)

# 5. CP → LP: logistics_provider.transportsTo matches consumer ports
for lp in logistics_providers:
    for cp_id in lp['to']:
        add_tfl('cp_' + cp_id, 'lp_' + lp['id'])

# 6. LP → PP: logistics_provider.transportsFrom matches producer ports
for lp in logistics_providers:
    for pp_id in lp['from']:
        add_tfl('lp_' + lp['id'], 'pp_' + pp_id)

# 7. PP → EB: export broker's ports (producer ports they operate through)
for eb in export_brokers:
    for pp_id in eb['ports']:
        add_tfl('pp_' + pp_id, 'eb_' + eb['id'])

# 8. EB → PW: producer warehouse adjacentTo matches producer ports used by EB
pp_to_pw = {}
for pw in producer_warehouses:
    pw_inst = instances.get(pw['id'], {})
    pw_ports = pw_inst.get('obj', {}).get('adjacentTo', [])
    for p in pw_ports:
        pp_to_pw[p] = pw['id']

for eb in export_brokers:
    for pp_id in eb['ports']:
        pw_id = pp_to_pw.get(pp_id)
        if pw_id:
            add_tfl('eb_' + eb['id'], 'pw_' + pw_id)

# 9. PW → Farm: farm isLocatedIn country, warehouse isLocatedIn same country
for f in farm_map:
    country = f['country'].replace(' ', '_')
    ep = farm_export_port.get(f['country'])
    if ep:
        pw_id = pp_to_pw.get(ep)
        if pw_id:
            add_tfl('pw_' + pw_id, 'f_' + f['id'])

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
