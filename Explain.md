# CoffeeLand Ontology Dashboard — 작업 내용 정리

이 문서는 지금까지 이 저장소에서 진행된 작업을 정리한 것입니다. (최종 갱신: 2026-07-28)

## 1. 프로젝트 개요

커피 산업 전체 공급망(생산 → 가공 → 무역 → 물류 → 매장 운영)을 OWL/RDF 온톨로지로 모델링하고,
이를 웹 대시보드로 시각화한 프로젝트입니다.

- **온톨로지 탐색 대시보드**: https://doogiesdj.github.io/CoffeeLand_Ontology-dashboard/dashboard.html
- **데이터 분석 대시보드**: https://doogiesdj.github.io/coffeeland-web
- **소스 저장소**: https://github.com/doogiesdj/CoffeeLand_Ontology-dashboard

## 2. 저장소 구조

```
CoffeeLand_Ontology-dashboard/
├── .github/workflows/
│   ├── deploy.yml                 # RDF → JSON 변환 + GitHub Pages 배포
│   └── build-and-deploy.yml
├── data/
│   ├── coffeeland_final_v4.rdf    # ⭐ 온톨로지 원본 (Protégé로 편집)
│   └── coffeeland_data_enrichment.ttl
├── scripts/
│   ├── rdf_to_json.py             # RDF → JSON 변환 (핵심 파이프라인)
│   ├── enrich_import_brokers.py   # Import Broker 실제 무역 데이터 보강
│   ├── add_rdf_instances.js
│   └── enrich_resources.js
├── dashboard.html                 # 대시보드 본체 (5,592줄)
├── docs/                          # GitHub Pages 배포 폴더 (자동 생성, 커밋하지 않아도 CI가 채움)
│   ├── dashboard.html
│   ├── ontology_data.json
│   └── coffeeland_data.json
└── REFERENCES.md                  # Import Broker 관계 근거 자료(출처 링크)
```

**업데이트 흐름**: Protégé에서 `data/coffeeland_final_v4.rdf` 수정 → GitHub push →
GitHub Actions가 `rdf_to_json.py` 실행해 JSON 재생성 → `docs/`에 반영 → GitHub Pages 자동 배포 (약 2분 소요).

## 3. 온톨로지 규모 (2026-07-28 기준)

| 항목 | 수치 |
|---|---|
| 클래스 | 63개 |
| Object Property | 85개 |
| Data Property | 20개 |
| 전체 Triple | 6,269개 |
| 인스턴스(개체) | 563개 |

카테고리별 인스턴스 분포:

| 카테고리 | 클래스 수 | 인스턴스 수 |
|---|---|---|
| Location (국가/항구/도시/창고) | 4 | 153 |
| Organization (브랜드/브로커/물류사 등) | 9 | 98 |
| Product (음료/원두/장비/소모품) | 4 | 54 |
| Quality & Processing | 3 | 50 |
| Market & Economics | 1 | 5 |

## 4. 대시보드 기능 구성

`dashboard.html`의 좌측 내비게이션 기준:

- **Main**: Dashboard(요약), Graph(Cytoscape 기반 온톨로지 그래프 시각화), Categories, Statistics
- **Shop Operations**: 매장 운영 관련 개체 (All Operations 통합 뷰)
- **Menu & Service**: BeverageMenu(음료 메뉴), PosSystem, Recipe, TrainingProgram
- **Resources**: Equipment(장비), Ingredient(원재료), Consumable(소모품)
- **Partners**: EquipmentSupplier, IngredientVendor, MaintenanceService
- **Tools**: 데이터 업로드/다운로드
- **Analytics**: 외부 데이터 분석 대시보드(coffeeland-web) 링크

각 인스턴스 카드는 클릭 시 상세 모달을 띄우며, 국가/도시/항구/농장 등은 실제 지리 좌표와
커피 산업 관련 실데이터(생산량, 문화, 무역 등)를 포함합니다. 세계지도(Leaflet.js)에서
생산국-소비국 간 무역 루트(해상 경로 포함)를 시각화하는 기능도 포함되어 있습니다.

## 5. 지금까지의 주요 작업 이력 (시간순 요약)

1. **초기 구축**: dashboard.html 최초 작성, GitHub Actions 자동 배포 파이프라인 구성, RDF→JSON 변환 스크립트 작성
2. **온톨로지 확장**: Market & Economics(38개), 국가/항구/창고 좌표 및 연결관계, 소비국 13개국 항구·창고 추가
3. **공급망 연결 정비**: Producer Warehouse-Farm 연결, disconnected supply chain 노드 수정, Import/Export Broker 6→14 / 5→11, Port 15→25로 확장
4. **물류(Logistics Provider)**: 실제 존재하는 물류사 10곳 추가 및 데이터 보강
5. **브랜드 데이터**: CoffeeBrand 22개 추가(총 36개), 브랜드별 공급망 상세 속성/가격 정보 추가
6. **매장 운영 데이터**: BeverageMenu 40개, Equipment 14개, Ingredient 33개, Consumable 16개로 대폭 보강; Partners(장비공급사/원재료벤더/유지보수업체) 보강
7. **지도/무역 시각화**: 세계지도(Leaflet.js) 추가, 생산국-소비국 무역 루트 시각화, 해상 경로 좌표 다수 오류 수정(육지 통과 문제 등)
8. **상세 모달 기능**: Country/Port/City/Warehouse/Farm 상세 모달 추가 (실제 지리/커피산업 데이터 포함), 국기 표시(flagcdn.com 연동)
9. **UI/데이터 정합성 버그 수정**: 하위 클래스 인스턴스 재귀 탐색 로직 수정, Analytics 링크 복원, 카드 이미지 매칭 수정 등 다수
10. **최근 작업 (2026-04-02)**: Import Broker의 `mediates`/`usesWarehouse`/`transportsTo` 관계를 실제 무역업체 데이터 기반으로 재구성(`enrich_import_brokers.py`, `REFERENCES.md` 출처 14개사 정리), 15개 소비국의 Port-Logistics 연결 추가

## 6. 알려진 운영상 주의사항

- `dashboard.html`은 정상 상태에서 5,500줄 이상이어야 함. 과거 한 차례 축소된 버전(1,162줄)을
  원본으로 착각해 편집한 뒤 CI가 gh-pages를 덮어써 사이트 기능(Categories, Menu & Service,
  Resources, Analytics 링크 등)이 사라진 사고가 있었음. 수정 전 항상 줄 수를 확인할 것.
- `main`과 `gh-pages` 브랜치의 파일 내용이 다를 수 있으므로, 실제 배포본 확인 시 gh-pages 기준으로 볼 것.
- `rdf_to_json.py` 실행에는 `rdflib` 파이썬 패키지가 필요 (`pip install rdflib`).

## 7. 현재 상태 (2026-07-28 확인)

- `main`/`gh-pages` 모두 원격과 동기화 완료, working tree clean
- 최근 GitHub Actions 배포(`pages build and deployment`) 성공
- 마지막 커밋: 2026-04-02 (Import Broker 무역 데이터 재구성)
