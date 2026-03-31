const fs=require('fs');
const d=JSON.parse(fs.readFileSync('docs/ontology_data.json','utf8'));
const NS='http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#';

function find(arr, name) {
  for(const c of arr) {
    if(c.name===name) return c;
    if(c.children) { const r=find(c.children, name); if(r) return r; }
  }
  return null;
}

function addInst(className, instName, props) {
  const cls=find(d.classHierarchy, className);
  if(!cls) { console.log('NOT FOUND:', className); return; }
  if(!cls.instances.includes(instName)) {
    cls.instances.push(instName);
    cls.instanceCount=cls.instances.length;
  }
  d.instanceDetails[instName]={uri:NS+instName, types:[className], properties:props||{}};
}

// ═══ EQUIPMENT (14개) ═══
addInst('EspressoMachine','EM_LaMarzocco_Linea',{hasModel:'La Marzocco Linea PB',hasManufacturer:'La Marzocco',hasCountry:'Italy',hasPowerWatt:'3200'});
addInst('EspressoMachine','EM_Synesso_MVP',{hasModel:'Synesso MVP Hydra',hasManufacturer:'Synesso',hasCountry:'USA',hasPowerWatt:'4500'});
addInst('EspressoMachine','EM_Nuova_Simonelli',{hasModel:'Nuova Simonelli Aurelia',hasManufacturer:'Nuova Simonelli',hasCountry:'Italy',hasPowerWatt:'3800'});
addInst('EspressoMachine','EM_DeLonghi_Pro',{hasModel:'DeLonghi La Specialista',hasManufacturer:'DeLonghi',hasCountry:'Italy',hasPowerWatt:'1450'});
addInst('Grinder','GR_Mahlkonig_EK43',{hasModel:'Mahlkönig EK43S',hasManufacturer:'Mahlkönig',hasCountry:'Germany',hasBurrSize:'98mm'});
addInst('Grinder','GR_Baratza_Forte',{hasModel:'Baratza Forte BG',hasManufacturer:'Baratza',hasCountry:'USA',hasBurrSize:'54mm'});
addInst('Grinder','GR_Mazzer_Major',{hasModel:'Mazzer Major V',hasManufacturer:'Mazzer',hasCountry:'Italy',hasBurrSize:'83mm'});
addInst('IceMaker','IM_Hoshizaki_KM',{hasModel:'Hoshizaki KM-320MAJ',hasManufacturer:'Hoshizaki',hasCountry:'Japan',hasCapacityKg:'320'});
addInst('IceMaker','IM_Scotsman_NDE',{hasModel:'Scotsman NDE 654',hasManufacturer:'Scotsman',hasCountry:'USA',hasCapacityKg:'300'});
addInst('RoasterMachine','RM_Probat_P25',{hasModel:'Probat P25',hasManufacturer:'Probat',hasCountry:'Germany',hasCapacityKg:'25'});
addInst('RoasterMachine','RM_Giesen_W15',{hasModel:'Giesen W15A',hasManufacturer:'Giesen',hasCountry:'Netherlands',hasCapacityKg:'15'});
addInst('RoasterMachine','RM_Loring_S35',{hasModel:'Loring S35 Kestrel',hasManufacturer:'Loring',hasCountry:'USA',hasCapacityKg:'35'});
addInst('WaterFilter','WF_Brita_Purity',{hasModel:'Brita Purity C1100',hasManufacturer:'Brita',hasCountry:'Germany'});
addInst('WaterFilter','WF_Everpure_4C',{hasModel:'Everpure 4C',hasManufacturer:'Everpure',hasCountry:'USA'});

// ═══ INGREDIENT (추가 16개) ═══
addInst('Bakery','Ing_Croissant',{hasName:'Butter Croissant',hasType:'Pastry'});
addInst('Bakery','Ing_Muffin',{hasName:'Blueberry Muffin',hasType:'Pastry'});
addInst('Bakery','Ing_Scone',{hasName:'Classic Scone',hasType:'Pastry'});
addInst('Bakery','Ing_Brownie',{hasName:'Chocolate Brownie',hasType:'Dessert'});
addInst('Sauce','Ing_ChocolateSauce',{hasName:'Dark Chocolate Sauce',hasBrand:'Ghirardelli'});
addInst('Sauce','Ing_CaramelDrizzle',{hasName:'Caramel Drizzle',hasBrand:'Torani'});
addInst('Sauce','Ing_WhiteMocha',{hasName:'White Mocha Sauce',hasBrand:'Monin'});
addInst('Syrup','Ing_VanillaSyrup_Monin',{hasName:'Vanilla Syrup',hasBrand:'Monin',hasVolumeMl:'750'});
addInst('Syrup','Ing_HazelnutSyrup',{hasName:'Hazelnut Syrup',hasBrand:'Torani',hasVolumeMl:'750'});
addInst('Syrup','Ing_CaramelSyrup_Monin',{hasName:'Caramel Syrup',hasBrand:'Monin',hasVolumeMl:'750'});
addInst('Syrup','Ing_PumpkinSpice',{hasName:'Pumpkin Spice Syrup',hasBrand:'DaVinci',hasVolumeMl:'750'});
addInst('Syrup','Ing_HoneySyrup',{hasName:'Honey Syrup',hasBrand:'Monin',hasVolumeMl:'750'});
addInst('TeaBase','Ing_ChaiConcentrate',{hasName:'Chai Tea Concentrate',hasBrand:'Oregon Chai'});
addInst('TeaBase','Ing_MatchaPowder',{hasName:'Ceremonial Grade Matcha',hasBrand:'Ippodo',hasOrigin:'Kyoto, Japan'});
addInst('TeaBase','Ing_HibiscusTea',{hasName:'Hibiscus Herbal Tea',hasBrand:'Harney & Sons'});
addInst('TeaBase','Ing_EarlGrey',{hasName:'Earl Grey Tea',hasBrand:'Twinings',hasOrigin:'UK'});
addInst('Milk','Ing_OatMilk',{hasName:'Oat Milk',hasBrand:'Oatly'});
addInst('Milk','Ing_AlmondMilk',{hasName:'Almond Milk',hasBrand:'Califia Farms'});
addInst('Milk','Ing_SoyMilk',{hasName:'Soy Milk',hasBrand:'Silk'});
addInst('Milk','Ing_CoconutMilk',{hasName:'Coconut Milk',hasBrand:'So Delicious'});

// ═══ CONSUMABLE (18개) ═══
addInst('PaperCup','Con_SmallCup_8oz',{hasName:'Small Hot Cup 8oz',hasMaterial:'Double-wall Paper',hasSupplier:'Solo Cup Co'});
addInst('PaperCup','Con_MediumCup_12oz',{hasName:'Medium Hot Cup 12oz',hasMaterial:'Double-wall Paper',hasSupplier:'Solo Cup Co'});
addInst('PaperCup','Con_LargeCup_16oz',{hasName:'Large Hot Cup 16oz',hasMaterial:'Double-wall Paper',hasSupplier:'Solo Cup Co'});
addInst('PaperCup','Con_ColdCup_16oz',{hasName:'Cold Cup 16oz',hasMaterial:'PET Plastic',hasSupplier:'Dart Container'});
addInst('PaperCup','Con_ColdCup_24oz',{hasName:'Cold Cup 24oz',hasMaterial:'PET Plastic',hasSupplier:'Dart Container'});
addInst('TakeoutLid','Con_HotLid_Dome',{hasName:'Hot Cup Dome Lid',hasMaterial:'PS Plastic',hasSupplier:'Solo Cup Co'});
addInst('TakeoutLid','Con_HotLid_Sipthrough',{hasName:'Sip-through Hot Lid',hasMaterial:'PS Plastic',hasSupplier:'Eco-Products'});
addInst('TakeoutLid','Con_ColdLid_Flat',{hasName:'Flat Cold Lid',hasMaterial:'PET Plastic',hasSupplier:'Dart Container'});
addInst('Straw','Con_PaperStraw',{hasName:'Paper Straw',hasMaterial:'FSC Paper',hasSupplier:'Aardvark Straws'});
addInst('Straw','Con_BioplasticStraw',{hasName:'Bioplastic Straw (PLA)',hasMaterial:'PLA Bioplastic',hasSupplier:'World Centric'});
addInst('Straw','Con_ReedStraw',{hasName:'Reed Straw',hasMaterial:'Natural Reed',hasSupplier:'HAY! Straws'});
addInst('Napkin','Con_CocktailNapkin',{hasName:'Cocktail Napkin (1-ply)',hasMaterial:'Recycled Paper',hasSupplier:'Georgia-Pacific'});
addInst('Napkin','Con_LunchNapkin',{hasName:'Lunch Napkin (2-ply)',hasMaterial:'Virgin Pulp',hasSupplier:'Kimberly-Clark'});
addInst('Carrier','Con_2CupCarrier',{hasName:'2-Cup Carrier',hasMaterial:'Corrugated Board',hasSupplier:'Pactiv'});
addInst('Carrier','Con_4CupCarrier',{hasName:'4-Cup Carrier',hasMaterial:'Molded Pulp',hasSupplier:'Pactiv'});
addInst('Carrier','Con_ToteCarrier',{hasName:'Kraft Tote Bag',hasMaterial:'Kraft Paper',hasSupplier:'Novamont'});

// Remove old Machine_B
const eqCls=find(d.classHierarchy,'Equipment');
if(eqCls) { eqCls.instances=eqCls.instances.filter(i=>i!=='Machine_B'); eqCls.instanceCount=eqCls.instances.length; }
delete d.instanceDetails['Machine_B'];

fs.writeFileSync('docs/ontology_data.json', JSON.stringify(d, null, 2));

// Verify
console.log('=== 결과 검증 ===');
['Equipment','Ingredient','Consumable'].forEach(name=>{
  const cls=find(d.classHierarchy, name);
  if(cls){
    let total=cls.instanceCount;
    const kids=cls.children.map(c=>{total+=c.instanceCount; return c.name+'='+c.instanceCount;});
    console.log(name+': 총 '+total+'개 ('+kids.join(', ')+')');
  }
});
