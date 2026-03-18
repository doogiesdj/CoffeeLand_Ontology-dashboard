# CoffeeLand_Ontology-dashboard

커피랜드 온톨로지 대시보드 — GitHub Pages 자동 배포

## 🌐 사이트

| 사이트 | URL |
|--------|-----|
| 온톨로지 탐색 | https://doogiesdj.github.io/CoffeeLand_Ontology-dashboard/dashboard.html |
| 데이터 분석 | https://doogiesdj.github.io/coffeeland-web |

## 📁 저장소 구조

```
CoffeeLand_Ontology-dashboard/
├── .github/
│   └── workflows/
│       └── deploy.yml          ← GitHub Actions 자동 배포
├── data/
│   ├── coffeeland_final_v2.rdf ← ⭐ 온톨로지 파일 (업데이트 대상)
│   └── coffeeland_data_enrichment.ttl ← 보강 데이터
├── scripts/
│   └── rdf_to_json.py          ← RDF → JSON 변환 스크립트
└── docs/                       ← GitHub Pages 배포 폴더 (자동 생성)
    ├── dashboard.html
    ├── ontology_data.json
    └── coffeeland_data.json
```

## 🔄 온톨로지 업데이트 방법

1. Protégé에서 온톨로지 수정
2. `data/coffeeland_final_v2.rdf` 파일 교체 (GitHub에 업로드)
3. GitHub Actions가 자동으로:
   - `rdf_to_json.py` 실행 → JSON 재생성
   - GitHub Pages 자동 배포
4. 약 2분 후 사이트 자동 반영

## 🛠 로컬 테스트

```bash
pip install rdflib
python scripts/rdf_to_json.py
```
