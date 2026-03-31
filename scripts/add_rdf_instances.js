const fs=require('fs');
const rdfPath='data/coffeeland_final_v2.rdf';
let rdf=fs.readFileSync(rdfPath,'utf8');
const NS='http://www.semanticweb.org/boogi/ontologies/2025/11/untitled-ontology-2#';
const U=NS.replace('#','#'); // prefix

function inst(id, type, props) {
  let xml=`  <rdf:Description rdf:about="${NS}${id}">\n`;
  xml+=`    <rdf:type rdf:resource="${NS}${type}"/>\n`;
  xml+=`    <rdf:type rdf:resource="http://www.w3.org/2002/07/owl#NamedIndividual"/>\n`;
  for(const[k,v] of Object.entries(props)) {
    if(k.startsWith('ref:')) {
      xml+=`    <untitled-ontology-2:${k.slice(4)} rdf:resource="${NS}${v}"/>\n`;
    } else {
      const dt = typeof v==='number' ? (Number.isInteger(v)?'integer':'float') : 'string';
      xml+=`    <untitled-ontology-2:${k} rdf:datatype="http://www.w3.org/2001/XMLSchema#${dt}">${v}</untitled-ontology-2:${k}>\n`;
    }
  }
  xml+=`  </rdf:Description>\n`;
  return xml;
}

let block='\n  <!-- ═══ NEW BeverageMenu Individuals (20) ═══ -->\n\n';
const newBev=[
  {id:'Ristretto',cat:'Espresso',temp:'Hot',cal:3,caf:75,rat:4.4,ps:2.5,desc:'Very short espresso pull, intense and concentrated'},
  {id:'Lungo',cat:'Espresso',temp:'Hot',cal:5,caf:90,rat:4.2,ps:2.8,desc:'Long-pull espresso, milder flavor with more volume'},
  {id:'Cafe_au_Lait',cat:'Espresso',temp:'Hot',cal:140,caf:80,rat:4.4,ps:3.5,desc:'Equal parts brewed coffee and steamed milk, French classic'},
  {id:'Espresso_Con_Panna',cat:'Espresso',temp:'Hot',cal:60,caf:63,rat:4.3,ps:3.0,desc:'Espresso topped with a dollop of whipped cream'},
  {id:'Doppio',cat:'Espresso',temp:'Hot',cal:10,caf:126,rat:4.4,ps:3.0,desc:'Double shot of espresso, bold and full-bodied'},
  {id:'Vienna_Coffee',cat:'Signature',temp:'Hot',cal:180,caf:95,rat:4.5,ps:4.5,desc:'Strong espresso topped with whipped cream and chocolate powder'},
  {id:'Irish_Coffee',cat:'Signature',temp:'Hot',cal:210,caf:80,rat:4.6,ps:6.0,desc:'Hot coffee with Irish whiskey, sugar, and cream'},
  {id:'Cafe_Bombon',cat:'Signature',temp:'Hot',cal:220,caf:63,rat:4.3,ps:4.0,desc:'Spanish-style espresso with sweetened condensed milk'},
  {id:'Einspanner',cat:'Signature',temp:'Hot',cal:190,caf:126,rat:4.5,ps:5.0,desc:'Austrian double espresso topped with whipped cream'},
  {id:'Honey_Latte',cat:'Signature',temp:'Hot',cal:230,caf:75,rat:4.6,ps:4.5,desc:'Espresso with steamed milk and honey drizzle'},
  {id:'Shakerato',cat:'Cold_Blended',temp:'Cold',cal:40,caf:95,rat:4.4,ps:4.5,desc:'Italian iced espresso shaken with ice and sugar'},
  {id:'Iced_Cappuccino',cat:'Cold_Blended',temp:'Cold',cal:130,caf:75,rat:4.5,ps:4.0,desc:'Chilled espresso with cold milk foam over ice'},
  {id:'Frappuccino',cat:'Cold_Blended',temp:'Cold',cal:380,caf:65,rat:4.4,ps:4.5,desc:'Blended iced coffee with milk, ice, and whipped cream'},
  {id:'Dalgona_Coffee',cat:'Cold_Blended',temp:'Cold',cal:260,caf:90,rat:4.3,ps:4.5,desc:'Whipped instant coffee foam over cold milk, Korean trend'},
  {id:'Chai_Latte',cat:'Tea',temp:'Hot',cal:200,caf:50,rat:4.5,ps:4.0,desc:'Spiced chai tea concentrate with steamed milk'},
  {id:'Matcha_Latte',cat:'Tea',temp:'Hot',cal:190,caf:70,rat:4.6,ps:4.5,desc:'Ceremonial grade matcha whisked with steamed milk'},
  {id:'Hot_Chocolate',cat:'Tea',temp:'Hot',cal:320,caf:5,rat:4.5,ps:3.5,desc:'Rich chocolate sauce blended with steamed milk'},
  {id:'Turkish_Coffee',cat:'Alternative',temp:'Hot',cal:10,caf:165,rat:4.5,ps:3.5,desc:'Finely ground coffee boiled in cezve, unfiltered'},
  {id:'Moka_Pot',cat:'Alternative',temp:'Hot',cal:5,caf:130,rat:4.3,ps:3.5,desc:'Stovetop brewed coffee, Italian Bialetti style'},
  {id:'Decaf_Latte',cat:'Decaf',temp:'Hot',cal:190,caf:5,rat:4.2,ps:4.0,desc:'Decaffeinated espresso with steamed milk'},
];
newBev.forEach(b=>{
  if(!rdf.includes(`#${b.id}">`)) {
    block+=inst(b.id,'BeverageMenu',{
      hasBeverageName:b.id.replace(/_/g,' '),hasCategory:b.cat,hasTemperature:b.temp,
      hasCalories:b.cal,hasCaffeineContent:b.caf,hasRating:b.rat,hasPriceSmall:b.ps,
      hasDescription:b.desc
    });
  }
});

block+='\n  <!-- ═══ NEW Equipment Individuals (14) ═══ -->\n\n';
const equip=[
  {id:'EM_LaMarzocco_Linea',type:'EspressoMachine',model:'La Marzocco Linea PB',mfr:'La Marzocco',country:'Italy',power:3200},
  {id:'EM_Synesso_MVP',type:'EspressoMachine',model:'Synesso MVP Hydra',mfr:'Synesso',country:'USA',power:4500},
  {id:'EM_Nuova_Simonelli',type:'EspressoMachine',model:'Nuova Simonelli Aurelia',mfr:'Nuova Simonelli',country:'Italy',power:3800},
  {id:'EM_DeLonghi_Pro',type:'EspressoMachine',model:'DeLonghi La Specialista',mfr:'DeLonghi',country:'Italy',power:1450},
  {id:'GR_Mahlkonig_EK43',type:'Grinder',model:'Mahlkönig EK43S',mfr:'Mahlkönig',country:'Germany'},
  {id:'GR_Baratza_Forte',type:'Grinder',model:'Baratza Forte BG',mfr:'Baratza',country:'USA'},
  {id:'GR_Mazzer_Major',type:'Grinder',model:'Mazzer Major V',mfr:'Mazzer',country:'Italy'},
  {id:'IM_Hoshizaki_KM',type:'IceMaker',model:'Hoshizaki KM-320MAJ',mfr:'Hoshizaki',country:'Japan'},
  {id:'IM_Scotsman_NDE',type:'IceMaker',model:'Scotsman NDE 654',mfr:'Scotsman',country:'USA'},
  {id:'RM_Probat_P25',type:'RoasterMachine',model:'Probat P25',mfr:'Probat',country:'Germany'},
  {id:'RM_Giesen_W15',type:'RoasterMachine',model:'Giesen W15A',mfr:'Giesen',country:'Netherlands'},
  {id:'RM_Loring_S35',type:'RoasterMachine',model:'Loring S35 Kestrel',mfr:'Loring',country:'USA'},
  {id:'WF_Brita_Purity',type:'WaterFilter',model:'Brita Purity C1100',mfr:'Brita',country:'Germany'},
  {id:'WF_Everpure_4C',type:'WaterFilter',model:'Everpure 4C',mfr:'Everpure',country:'USA'},
];
equip.forEach(e=>{
  if(!rdf.includes(`#${e.id}">`)) {
    const p={hasModel:e.model,hasManufacturer:e.mfr,hasCountry:e.country};
    if(e.power) p.hasPowerWatt=e.power;
    block+=inst(e.id,e.type,p);
  }
});

block+='\n  <!-- ═══ NEW Ingredient Individuals (20) ═══ -->\n\n';
const ingr=[
  {id:'Ing_Croissant',type:'Bakery',name:'Butter Croissant'},{id:'Ing_Muffin',type:'Bakery',name:'Blueberry Muffin'},
  {id:'Ing_Scone',type:'Bakery',name:'Classic Scone'},{id:'Ing_Brownie',type:'Bakery',name:'Chocolate Brownie'},
  {id:'Ing_ChocolateSauce_GH',type:'Sauce',name:'Dark Chocolate Sauce',brand:'Ghirardelli'},
  {id:'Ing_CaramelDrizzle',type:'Sauce',name:'Caramel Drizzle',brand:'Torani'},
  {id:'Ing_WhiteMocha',type:'Sauce',name:'White Mocha Sauce',brand:'Monin'},
  {id:'Ing_VanillaSyrup_M',type:'Syrup',name:'Vanilla Syrup',brand:'Monin'},
  {id:'Ing_HazelnutSyrup',type:'Syrup',name:'Hazelnut Syrup',brand:'Torani'},
  {id:'Ing_CaramelSyrup_M',type:'Syrup',name:'Caramel Syrup',brand:'Monin'},
  {id:'Ing_PumpkinSpice',type:'Syrup',name:'Pumpkin Spice Syrup',brand:'DaVinci'},
  {id:'Ing_HoneySyrup',type:'Syrup',name:'Honey Syrup',brand:'Monin'},
  {id:'Ing_ChaiConcentrate',type:'TeaBase',name:'Chai Tea Concentrate',brand:'Oregon Chai'},
  {id:'Ing_MatchaPowder',type:'TeaBase',name:'Ceremonial Grade Matcha',brand:'Ippodo'},
  {id:'Ing_HibiscusTea',type:'TeaBase',name:'Hibiscus Herbal Tea',brand:'Harney & Sons'},
  {id:'Ing_EarlGrey',type:'TeaBase',name:'Earl Grey Tea',brand:'Twinings'},
  {id:'Ing_OatMilk',type:'Milk',name:'Oat Milk',brand:'Oatly'},
  {id:'Ing_AlmondMilk',type:'Milk',name:'Almond Milk',brand:'Califia Farms'},
  {id:'Ing_SoyMilk',type:'Milk',name:'Soy Milk',brand:'Silk'},
  {id:'Ing_CoconutMilk',type:'Milk',name:'Coconut Milk',brand:'So Delicious'},
];
ingr.forEach(i=>{
  if(!rdf.includes(`#${i.id}">`)) {
    const p={hasName:i.name};
    if(i.brand) p.hasBrand=i.brand;
    block+=inst(i.id,i.type,p);
  }
});

block+='\n  <!-- ═══ NEW Consumable Individuals (16) ═══ -->\n\n';
const cons=[
  {id:'Con_SmallCup_8oz',type:'PaperCup',name:'Small Hot Cup 8oz',mat:'Double-wall Paper'},
  {id:'Con_MediumCup_12oz',type:'PaperCup',name:'Medium Hot Cup 12oz',mat:'Double-wall Paper'},
  {id:'Con_LargeCup_16oz',type:'PaperCup',name:'Large Hot Cup 16oz',mat:'Double-wall Paper'},
  {id:'Con_ColdCup_16oz',type:'PaperCup',name:'Cold Cup 16oz',mat:'PET Plastic'},
  {id:'Con_ColdCup_24oz',type:'PaperCup',name:'Cold Cup 24oz',mat:'PET Plastic'},
  {id:'Con_HotLid_Dome',type:'TakeoutLid',name:'Hot Cup Dome Lid',mat:'PS Plastic'},
  {id:'Con_HotLid_Sipthrough',type:'TakeoutLid',name:'Sip-through Hot Lid',mat:'PS Plastic'},
  {id:'Con_ColdLid_Flat',type:'TakeoutLid',name:'Flat Cold Lid',mat:'PET Plastic'},
  {id:'Con_PaperStraw',type:'Straw',name:'Paper Straw',mat:'FSC Paper'},
  {id:'Con_BioplasticStraw',type:'Straw',name:'Bioplastic Straw (PLA)',mat:'PLA Bioplastic'},
  {id:'Con_ReedStraw',type:'Straw',name:'Reed Straw',mat:'Natural Reed'},
  {id:'Con_CocktailNapkin',type:'Napkin',name:'Cocktail Napkin (1-ply)',mat:'Recycled Paper'},
  {id:'Con_LunchNapkin',type:'Napkin',name:'Lunch Napkin (2-ply)',mat:'Virgin Pulp'},
  {id:'Con_2CupCarrier',type:'Carrier',name:'2-Cup Carrier',mat:'Corrugated Board'},
  {id:'Con_4CupCarrier',type:'Carrier',name:'4-Cup Carrier',mat:'Molded Pulp'},
  {id:'Con_ToteCarrier',type:'Carrier',name:'Kraft Tote Bag',mat:'Kraft Paper'},
];
cons.forEach(c=>{
  if(!rdf.includes(`#${c.id}">`)) {
    block+=inst(c.id,c.type,{hasName:c.name,hasMaterial:c.mat});
  }
});

// Insert before </rdf:RDF>
rdf=rdf.replace('</rdf:RDF>', block+'\n</rdf:RDF>');
fs.writeFileSync(rdfPath, rdf);
console.log('RDF updated! New BeverageMenu + Equipment + Ingredient + Consumable instances added.');
