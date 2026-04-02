#!/usr/bin/env python3
"""
Enrich ImportBroker individuals in coffeeland_final_v4.rdf with real-world data.
Adds: mediates (brands), usesWarehouse (consumer warehouses), transportsTo (consumer ports).

Research sources documented in REFERENCES.md.
"""
import os, re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RDF_FILE = os.path.join(BASE_DIR, 'data', 'coffeeland_final_v4.rdf')
NS = "http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#"

# ═══════════════════════════════════════════════════════════════
# REAL-WORLD DATA MAPPINGS  (based on web research — see REFERENCES.md)
# ═══════════════════════════════════════════════════════════════

# Brand → Broker (which brokers handle which brands, based on origin-country match + specialization)
# Each brand gets 2–4 primary brokers = realistic
BROKER_BRANDS = {
    "Falcon_Coffees": [
        "Kenya_AA", "Nyeri_Peaberry",                        # Kenya — origin office
        "Yirgacheffe_Special", "Sidamo_Natural",             # Ethiopia — origin office
        "Bugisu_AA",                                          # Uganda — origin office
        "Rwandan_Bourbon",                                    # Rwanda — origin office
        "Colombian_Supremo", "Huila_Reserve",                # Colombia
        "Peruvian_Organic",                                   # Peru — SARL office
        "Sulawesi_Toraja", "Sumatra_Mandheling",             # Indonesia
        "Da_Lat_Arabica",                                     # Vietnam
    ],
    "Sustainable_Harvest": [
        "Colombian_Supremo", "Narino_Supremo",               # Colombia — origin office
        "Peruvian_Organic",                                   # Peru — origin office
        "Honduras_SHG", "Marcala_Organic",                   # Honduras
        "Huehuetenango_SHB",                                  # Guatemala
        "Matagalpa_SHG",                                      # Nicaragua
        "Rwandan_Bourbon",                                    # Rwanda
        "Yirgacheffe_Special",                                # Ethiopia
    ],
    "Schluter_SA": [
        "Yirgacheffe_Special", "Sidamo_Natural", "Harrar_Longberry",  # Ethiopia — specialty
        "Kenya_AA", "Nyeri_Peaberry",                                  # Kenya
        "Kilimanjaro_Peaberry",                                        # Tanzania
        "Rwandan_Bourbon",                                              # Rwanda
        "Bugisu_AA",                                                    # Uganda
    ],
    "Ally_Coffee": [
        "Bourbon_Santos", "Santos_Premium", "Cerrado_Natural",  # Brazil — vertical integration
        "Colombian_Supremo", "Narino_Supremo",                  # Colombia — sourcing office
        "Tarrazu_Reserve", "West_Valley_Honey",                 # Costa Rica — sourcing office
        "Yirgacheffe_Special",                                   # Ethiopia — sourcing office
        "Antigua_Premium",                                       # Guatemala
    ],
    "Sucafina": [
        "Bourbon_Santos", "Santos_Premium", "Cerrado_Natural",  # Brazil — major operations
        "Huila_Reserve", "Narino_Supremo",                       # Colombia
        "Kilimanjaro_Peaberry",                                   # Tanzania
        "Kenya_AA",                                               # Kenya
        "Rwandan_Bourbon",                                        # Rwanda
        "Bugisu_AA",                                              # Uganda
        "Peruvian_Organic",                                       # Peru
        "Honduras_SHG",                                           # Honduras
        "Blue_Mountain_Supreme",                                  # Jamaica
        "Da_Lat_Arabica", "Robusta_Select",                      # Vietnam
        "Sulawesi_Toraja", "Sumatra_Mandheling",                 # Indonesia
        "PNG_Sigri",                                              # PNG
    ],
    "Neumann_Kaffee_Gruppe": [
        "Bourbon_Santos", "Santos_Premium", "Cerrado_Natural",  # Brazil — farm ownership
        "Colombian_Supremo",                                      # Colombia — SKN Caribecafe
        "Chiapas_Altura",                                         # Mexico — Exportadora de Cafe
        "Honduras_SHG", "Marcala_Organic",                       # Honduras
        "Kenya_AA", "Nyeri_Peaberry",                             # Kenya — Ibero Kenya
        "Bugisu_AA",                                              # Uganda — Ibero Uganda
        "Kilimanjaro_Peaberry",                                   # Tanzania
        "Da_Lat_Arabica", "Robusta_Select",                      # Vietnam — NKG Vietnam
        "Sulawesi_Toraja", "Java_Estate", "Sumatra_Mandheling",  # Indonesia — PT NKG
        "Malabar_Monsoon",                                        # India — NKG India
        "PNG_Sigri",                                              # PNG
    ],
    "Itochu_Coffee": [
        "Antigua_Premium", "Huehuetenango_SHB",  # Guatemala — UNEX subsidiary
        "Sulawesi_Toraja", "Java_Estate",          # Indonesia — PT Aneka
        "Bourbon_Santos",                           # Brazil
        "Yirgacheffe_Special",                      # Ethiopia
    ],
    "Green_Coffee_Traders": [
        "Blue_Mountain_Supreme",    # Jamaica — niche specialty
        "Kona_Extra_Fancy",         # Hawaii — niche specialty
        "Mocha_Sanani",             # Yemen — niche specialty
        "Antigua_Premium",          # Guatemala
        "Tarrazu_Reserve",          # Costa Rica
        "Java_Estate",              # Indonesia
    ],
    "Atlantic_Coffee": [
        "Bourbon_Santos", "Cerrado_Natural",        # Brazil — ECOM network
        "Colombian_Supremo",                         # Colombia
        "Da_Lat_Arabica", "Robusta_Select",          # Vietnam — ECOM strong
        "Honduras_SHG",                               # Honduras
        "Malabar_Monsoon",                            # India
        "Sulawesi_Toraja",                            # Indonesia
    ],
    "Caravela_Coffee": [
        "Colombian_Supremo", "Narino_Supremo", "Huila_Reserve",  # Colombia — HQ, largest ops
        "Pacamara_Reserve",                                        # El Salvador
        "Antigua_Premium", "Huehuetenango_SHB",                   # Guatemala
        "Chiapas_Altura",                                          # Mexico
        "Matagalpa_SHG",                                           # Nicaragua
        "Peruvian_Organic",                                        # Peru
    ],
    "Volcafe": [
        "Bourbon_Santos", "Santos_Premium", "Cerrado_Natural",   # Brazil — Santos office
        "Colombian_Supremo",                                       # Colombia — Carcafe
        "Tarrazu_Reserve", "West_Valley_Honey",                   # Costa Rica — multiple mills
        "Antigua_Premium", "Huehuetenango_SHB",                   # Guatemala — Waelti-Schoenfeld
        "Honduras_SHG", "Marcala_Organic",                        # Honduras — Molinos
        "Kenya_AA",                                                # Kenya — Taylor Winch
        "Kilimanjaro_Peaberry",                                    # Tanzania — Taylor Winch
        "Peruvian_Organic",                                        # Peru — Prodelsur
        "Da_Lat_Arabica",                                          # Vietnam
        "PNG_Sigri",                                               # PNG — PNG Coffee Exports
    ],
    "Westfeldt_Brothers": [
        "Bourbon_Santos", "Santos_Premium",      # Brazil — traditional strength
        "Colombian_Supremo",                      # Colombia
        "Tarrazu_Reserve",                        # Costa Rica
        "Chiapas_Altura",                         # Mexico
        "Antigua_Premium",                        # Guatemala
        "Honduras_SHG",                           # Honduras
    ],
    "Cofinet": [
        "Colombian_Supremo", "Narino_Supremo", "Huila_Reserve",  # Colombia — family farm origin
        "Peruvian_Organic",                                        # Peru — recent expansion
    ],
    "Strauss_Coffee": [
        "Bourbon_Santos", "Santos_Premium", "Cerrado_Natural",   # Brazil — Tres Coracoes JV
        "Robusta_Select",                                          # Vietnam — global procurement
    ],
}

# Broker → Consumer Warehouses (confirmed/strong evidence of warehouse presence)
BROKER_WAREHOUSES = {
    "Falcon_Coffees": [
        "Warehouse_Felixstowe_East",     # UK — Vollers Bury St Edmunds
        "Warehouse_Antwerp_North",       # Belgium — PGS warehouse
        "Warehouse_LongBeach_South",     # USA — Oakland/CA
        "Warehouse_NewOrleans_CBD",      # USA — Dupuy Houston area
    ],
    "Sustainable_Harvest": [
        "Warehouse_LongBeach_South",     # USA — Oakland, CA
        "Warehouse_Seattle_Port",        # USA — Portland/Auburn, WA
    ],
    "Schluter_SA": [
        "Warehouse_Felixstowe_East",     # UK — Liverpool office, Vollers
        "Warehouse_Hamburg_Central",     # Germany — Hamburg warehouse
        "Warehouse_Antwerp_North",       # Belgium — Vollers network
    ],
    "Ally_Coffee": [
        "Warehouse_Hamburg_Central",     # Germany — Schwarze & Consort
        "Warehouse_Felixstowe_East",     # UK — Vollers UK
        "Warehouse_LongBeach_South",     # USA — San Leandro/LA
        "Warehouse_Seattle_Port",        # USA — Auburn, WA
        "Warehouse_Singapore_West",      # Singapore — TVS SCS
        "Warehouse_Sydney_South",        # Australia — RPM Freight
        "Warehouse_Melbourne_Docks",     # Australia — RPM Derrimut
        "Warehouse_Vancouver",           # Canada — confirmed
    ],
    "Sucafina": [
        "Warehouse_Antwerp_North",       # Belgium — Pacorini, HQ office
        "Warehouse_Hamburg_Central",     # Germany — Vollers
        "Warehouse_Shanghai",            # China — Kunshan bonded
        "Warehouse_Sydney_South",        # Australia — bonded
        "Warehouse_Melbourne_Docks",     # Australia — bonded
        "Warehouse_Singapore_West",      # Singapore — APAC
        "Warehouse_Miami_FreeZone",      # USA — Fort Lauderdale
        "Warehouse_Seattle_Port",        # USA — Auburn, WA
        "Warehouse_LongBeach_South",     # USA — West Coast
    ],
    "Neumann_Kaffee_Gruppe": [
        "Warehouse_Hamburg_Central",     # Germany — NKG Kala, CoffeePlaza HQ
        "Warehouse_Genoa_Harbor",        # Italy — Bero Italia
        "Warehouse_Gdansk",              # Poland — Bero Polska (Gdynia)
        "Warehouse_Singapore_West",      # Singapore — Bero Coffee
        "Warehouse_Busan_Port",          # South Korea — NKG Korea (Seoul)
        "Warehouse_Shanghai",            # China — NKG Shanghai
        "Warehouse_NewOrleans_CBD",      # USA — InterAmerican/Dupuy
        "Warehouse_LongBeach_South",     # USA — InterAmerican Oakland
        "Warehouse_Seattle_Port",        # USA — Atlas Coffee, Auburn
    ],
    "Itochu_Coffee": [
        "Warehouse_Tokyo_Bay",           # Japan — HQ, Itochu Logistics
        "Warehouse_Singapore_West",      # Singapore — ITOCHU SG
    ],
    "Green_Coffee_Traders": [
        "Warehouse_LongBeach_South",     # USA — West Coast
        "Warehouse_Vancouver",           # Canada
    ],
    "Atlantic_Coffee": [
        "Warehouse_Miami_FreeZone",      # USA — Houston/ECOM
        "Warehouse_LongBeach_South",     # USA — SF Bay Area (ASCI)
    ],
    "Caravela_Coffee": [
        "Warehouse_Felixstowe_East",     # UK — London HQ
        "Warehouse_Sydney_South",        # Australia — Sydney office
    ],
    "Volcafe": [
        "Warehouse_Hamburg_Central",     # Germany — Gollucke & Rothfos Bremen
        "Warehouse_Genoa_Harbor",        # Italy — Volcafe Italia
        "Warehouse_Barcelona_Port",      # Spain — Volcafe Iberia stock hub
        "Warehouse_Felixstowe_East",     # UK — Bristol lab, Vollers UK
        "Warehouse_Tokyo_Bay",           # Japan — Kobe
        "Warehouse_Shanghai",            # China — Volcafe China
        "Warehouse_Sydney_South",        # Australia — Cofi-Com Huntingwood
        "Warehouse_Singapore_West",      # Singapore
        "Warehouse_Piraeus",             # Greece — Volcafe Greece (Athens)
    ],
    "Westfeldt_Brothers": [
        "Warehouse_NewOrleans_CBD",      # USA — 528 Gravier St, sole hub
    ],
    "Cofinet": [
        "Warehouse_Sydney_South",        # Australia — founded Sydney
        "Warehouse_Singapore_West",      # Singapore — spot warehouse
        "Warehouse_Felixstowe_East",     # UK — spot warehouse
    ],
    "Strauss_Coffee": [
        "Warehouse_Amsterdam_West",      # Netherlands — operational HQ
        "Warehouse_Gdansk",              # Poland — MK Cafe ops
        "Warehouse_SaintPetersburg",     # Russia — Strunino factory
        "Warehouse_Prague",              # Czech Rep — Eastern Europe ops
    ],
}

# Broker → Consumer Ports (ports near their confirmed warehouse/office locations)
BROKER_PORTS = {
    "Falcon_Coffees": [
        "Port_Felixstowe",       # UK
        "Port_Antwerp",          # Belgium
        "Port_LongBeach",        # USA West Coast
        "Port_NewOrleans",       # USA Gulf
        "Port_NewYork",          # USA East Coast
    ],
    "Sustainable_Harvest": [
        "Port_LongBeach",        # USA — Oakland
        "Port_Seattle",          # USA — Portland/Auburn
        "Port_NewYork",          # USA — NJ warehouse
    ],
    "Schluter_SA": [
        "Port_Felixstowe",       # UK — Liverpool
        "Port_Hamburg",           # Germany
        "Port_Antwerp",          # Belgium
    ],
    "Ally_Coffee": [
        "Port_Hamburg",           # Germany
        "Port_Felixstowe",       # UK
        "Port_LongBeach",        # USA
        "Port_Seattle",          # USA
        "Port_Singapore",        # Singapore
        "Port_Sydney",           # Australia
        "Port_Vancouver",        # Canada
    ],
    "Sucafina": [
        "Port_Antwerp",          # Belgium — HQ
        "Port_Hamburg",           # Germany
        "Port_Shanghai",         # China — Kunshan
        "Port_Sydney",           # Australia
        "Port_Singapore",        # Singapore
        "Port_LongBeach",        # USA
        "Port_Seattle",          # USA
        "Port_NewYork",          # USA — NJ
        "Port_Montreal",         # Canada
    ],
    "Neumann_Kaffee_Gruppe": [
        "Port_Hamburg",           # Germany — HQ, Kala
        "Port_Genoa",            # Italy — Bero Italia
        "Port_Gdansk",           # Poland — Bero Polska
        "Port_Singapore",        # Singapore — Bero Coffee
        "Port_Busan",            # South Korea — NKG Korea
        "Port_Shanghai",         # China — NKG Shanghai
        "Port_NewOrleans",       # USA — InterAmerican
        "Port_LongBeach",        # USA — Oakland
        "Port_Seattle",          # USA — Atlas Coffee
        "Port_NewYork",          # USA — Hoboken NJ
    ],
    "Itochu_Coffee": [
        "Port_Tokyo",            # Japan — HQ
        "Port_Singapore",        # Singapore — ITOCHU SG
        "Port_Busan",            # South Korea — regional
    ],
    "Green_Coffee_Traders": [
        "Port_LongBeach",        # USA
        "Port_Vancouver",        # Canada
        "Port_NewYork",          # USA
    ],
    "Atlantic_Coffee": [
        "Port_LongBeach",        # USA — ASCI Bay Area
        "Port_NewOrleans",       # USA — Houston nearby
    ],
    "Caravela_Coffee": [
        "Port_Felixstowe",       # UK — London HQ
        "Port_Sydney",           # Australia
        "Port_NewYork",          # USA — East Coast
    ],
    "Volcafe": [
        "Port_Hamburg",           # Germany — Bremen
        "Port_Genoa",            # Italy
        "Port_Valencia",         # Spain — Iberia
        "Port_Felixstowe",       # UK
        "Port_Tokyo",            # Japan — Kobe
        "Port_Shanghai",         # China
        "Port_Sydney",           # Australia — Cofi-Com
        "Port_Singapore",        # Singapore
        "Port_Piraeus",          # Greece — Athens
        "Port_NewYork",          # USA — Irvington NY
        "Port_LongBeach",        # USA
    ],
    "Westfeldt_Brothers": [
        "Port_NewOrleans",       # USA — sole hub
    ],
    "Cofinet": [
        "Port_Sydney",           # Australia — founded
        "Port_Singapore",        # Singapore
        "Port_Felixstowe",       # UK
    ],
    "Strauss_Coffee": [
        "Port_Rotterdam",        # Netherlands — Amsterdam HQ
        "Port_Gdansk",           # Poland — MK Cafe
        "Port_SaintPetersburg",  # Russia — Strunino
        "Port_Istanbul",         # Turkey/Middle East
    ],
}


def build_triples():
    """Generate RDF/XML triples for each import broker."""
    lines = []
    for broker_id, brand_ids in BROKER_BRANDS.items():
        for brand_id in brand_ids:
            lines.append(f'    <cof:mediates rdf:resource="{NS}{brand_id}"/>')

    for broker_id, wh_ids in BROKER_WAREHOUSES.items():
        for wh_id in wh_ids:
            lines.append(f'    <cof:usesWarehouse rdf:resource="{NS}{wh_id}"/>')

    for broker_id, port_ids in BROKER_PORTS.items():
        for port_id in port_ids:
            lines.append(f'    <cof:transportsTo rdf:resource="{NS}{port_id}"/>')

    return lines


def update_rdf():
    with open(RDF_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    changes = 0
    for broker_id in BROKER_BRANDS:
        brands = BROKER_BRANDS.get(broker_id, [])
        warehouses = BROKER_WAREHOUSES.get(broker_id, [])
        ports = BROKER_PORTS.get(broker_id, [])

        # Build new properties block
        new_props = []
        for b in brands:
            new_props.append(f'    <cof:mediates rdf:resource="{NS}{b}"/>')
        for w in warehouses:
            new_props.append(f'    <cof:usesWarehouse rdf:resource="{NS}{w}"/>')
        for p in ports:
            new_props.append(f'    <cof:transportsTo rdf:resource="{NS}{p}"/>')
        new_block = '\n'.join(new_props)

        # Find the broker's rdf:Description block and add properties before </rdf:Description>
        pattern = (
            rf'(<rdf:Description rdf:about="{re.escape(NS)}{re.escape(broker_id)}">'
            rf'.*?)'
            rf'(  </rdf:Description>)'
        )
        match = re.search(pattern, content, re.DOTALL)
        if match:
            # Remove any existing mediates/usesWarehouse/transportsTo for this broker
            block = match.group(1)
            block = re.sub(r'\n    <cof:mediates [^/]*/>', '', block)
            block = re.sub(r'\n    <cof:usesWarehouse [^/]*/>', '', block)
            block = re.sub(r'\n    <cof:transportsTo [^/]*/>', '', block)

            replacement = block + '\n' + new_block + '\n' + match.group(2)
            content = content[:match.start()] + replacement + content[match.end():]
            changes += 1
            print(f"  {broker_id}: +{len(brands)} brands, +{len(warehouses)} warehouses, +{len(ports)} ports")

    with open(RDF_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\nUpdated {changes} import brokers in RDF")
    total_mediates = sum(len(v) for v in BROKER_BRANDS.values())
    total_warehouses = sum(len(v) for v in BROKER_WAREHOUSES.values())
    total_ports = sum(len(v) for v in BROKER_PORTS.values())
    print(f"Total: {total_mediates} mediates + {total_warehouses} usesWarehouse + {total_ports} transportsTo = {total_mediates+total_warehouses+total_ports} new triples")


if __name__ == '__main__':
    print("=== Enriching Import Brokers with real-world data ===\n")
    update_rdf()
    print("\nDone! Run rdf_to_json.py next to regenerate JSON.")
