// Shared country → states map used across Customers, Vendors, Warehouses, Settings.
// statesFor(country) returns [] for countries not in the map — callers should show
// a free-text input when the array is empty.

export const COUNTRY_STATES = {
  "India": [
    "Andaman and Nicobar Islands","Andhra Pradesh","Arunachal Pradesh","Assam","Bihar",
    "Chandigarh","Chhattisgarh","Dadra and Nagar Haveli and Daman and Diu","Delhi",
    "Goa","Gujarat","Haryana","Himachal Pradesh","Jammu and Kashmir","Jharkhand",
    "Karnataka","Kerala","Ladakh","Lakshadweep","Madhya Pradesh","Maharashtra",
    "Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Puducherry","Punjab",
    "Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
    "Uttarakhand","West Bengal",
  ],
  "United States": [
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
    "Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa",
    "Kansas","Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan",
    "Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada",
    "New Hampshire","New Jersey","New Mexico","New York","North Carolina",
    "North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island",
    "South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont",
    "Virginia","Washington","West Virginia","Wisconsin","Wyoming",
    "District of Columbia",
  ],
  "United Kingdom": ["England","Scotland","Wales","Northern Ireland"],
  "Australia": [
    "Australian Capital Territory","New South Wales","Northern Territory",
    "Queensland","South Australia","Tasmania","Victoria","Western Australia",
  ],
  "Canada": [
    "Alberta","British Columbia","Manitoba","New Brunswick",
    "Newfoundland and Labrador","Northwest Territories","Nova Scotia","Nunavut",
    "Ontario","Prince Edward Island","Quebec","Saskatchewan","Yukon",
  ],
  "United Arab Emirates": [
    "Abu Dhabi","Ajman","Dubai","Fujairah","Ras Al Khaimah","Sharjah","Umm Al Quwain",
  ],
  "Oman": [
    "Muscat","Dhofar","Musandam","Al Buraimi","Ad Dakhiliyah","Al Batinah North",
    "Al Batinah South","Al Sharqiyah North","Al Sharqiyah South","Adh Dhahirah","Al Wusta",
  ],
  "Germany": [
    "Baden-Württemberg","Bavaria","Berlin","Brandenburg","Bremen","Hamburg",
    "Hesse","Lower Saxony","Mecklenburg-Vorpommern","North Rhine-Westphalia",
    "Rhineland-Palatinate","Saarland","Saxony","Saxony-Anhalt",
    "Schleswig-Holstein","Thuringia",
  ],
  "France": [
    "Auvergne-Rhône-Alpes","Bourgogne-Franche-Comté","Brittany",
    "Centre-Val de Loire","Corsica","Grand Est","Hauts-de-France",
    "Île-de-France","Normandy","Nouvelle-Aquitaine","Occitanie",
    "Pays de la Loire","Provence-Alpes-Côte d'Azur",
  ],
  "Singapore": [
    "Central Region","East Region","North Region","North-East Region","West Region",
  ],
  "Malaysia": [
    "Johor","Kedah","Kelantan","Kuala Lumpur","Labuan","Melaka","Negeri Sembilan",
    "Pahang","Penang","Perak","Perlis","Putrajaya","Sabah","Sarawak","Selangor",
    "Terengganu",
  ],
  "Sri Lanka": [
    "Central","Eastern","North Central","Northern","North Western",
    "Sabaragamuwa","Southern","Uva","Western",
  ],
  "Saudi Arabia": [
    "Riyadh","Makkah","Madinah","Qassim","Eastern Province","Asir",
    "Tabuk","Hail","Northern Borders","Jazan","Najran","Bahah","Jawf",
  ],
  "Pakistan": [
    "Balochistan","Khyber Pakhtunkhwa","Punjab","Sindh",
    "Azad Kashmir","Gilgit-Baltistan","Islamabad Capital Territory",
  ],
  "Bangladesh": [
    "Barisal","Chittagong","Dhaka","Khulna","Mymensingh",
    "Rajshahi","Rangpur","Sylhet",
  ],
  "Nepal": [
    "Koshi","Madhesh","Bagmati","Gandaki","Lumbini",
    "Karnali","Sudurpashchim",
  ],
  "South Africa": [
    "Eastern Cape","Free State","Gauteng","KwaZulu-Natal","Limpopo",
    "Mpumalanga","Northern Cape","North West","Western Cape",
  ],
  "Brazil": [
    "Acre","Alagoas","Amapá","Amazonas","Bahia","Ceará","Espírito Santo",
    "Goiás","Maranhão","Mato Grosso","Mato Grosso do Sul","Minas Gerais",
    "Pará","Paraíba","Paraná","Pernambuco","Piauí","Rio de Janeiro",
    "Rio Grande do Norte","Rio Grande do Sul","Rondônia","Roraima",
    "Santa Catarina","São Paulo","Sergipe","Tocantins","Distrito Federal",
  ],
  "China": [
    "Anhui","Beijing","Chongqing","Fujian","Gansu","Guangdong","Guangxi",
    "Guizhou","Hainan","Hebei","Heilongjiang","Henan","Hubei","Hunan",
    "Inner Mongolia","Jiangsu","Jiangxi","Jilin","Liaoning","Ningxia",
    "Qinghai","Shaanxi","Shandong","Shanghai","Shanxi","Sichuan","Tianjin",
    "Tibet","Xinjiang","Yunnan","Zhejiang",
  ],
  "Japan": [
    "Aichi","Akita","Aomori","Chiba","Ehime","Fukui","Fukuoka","Fukushima",
    "Gifu","Gunma","Hiroshima","Hokkaido","Hyogo","Ibaraki","Ishikawa",
    "Iwate","Kagawa","Kagoshima","Kanagawa","Kochi","Kumamoto","Kyoto",
    "Mie","Miyagi","Miyazaki","Nagano","Nagasaki","Nara","Niigata","Oita",
    "Okayama","Okinawa","Osaka","Saga","Saitama","Shiga","Shimane","Shizuoka",
    "Tochigi","Tokushima","Tokyo","Tottori","Toyama","Wakayama","Yamagata",
    "Yamaguchi","Yamanashi",
  ],
};

// Full alphabetical country list — countries with a states map come first.
const _mapped = Object.keys(COUNTRY_STATES);
const _rest = [
  "Afghanistan","Albania","Algeria","Angola","Argentina","Austria","Azerbaijan",
  "Bahrain","Belgium","Bolivia","Bulgaria","Cambodia","Chile","Colombia","Croatia",
  "Cyprus","Czech Republic","Denmark","Ecuador","Egypt","Estonia","Ethiopia",
  "Finland","Ghana","Greece","Guatemala","Honduras","Hungary","Indonesia","Iran",
  "Iraq","Ireland","Israel","Italy","Jamaica","Jordan","Kazakhstan","Kenya",
  "Kuwait","Latvia","Lebanon","Lithuania","Luxembourg","Maldives","Malta",
  "Mexico","Morocco","Myanmar","Netherlands","New Zealand","Nigeria","Norway",
  "Oman","Panama","Peru","Philippines","Poland","Portugal","Qatar","Romania",
  "Russia","Senegal","Serbia","Slovakia","Slovenia","South Korea","Spain",
  "Sweden","Switzerland","Taiwan","Tanzania","Thailand","Tunisia","Turkey",
  "Uganda","Ukraine","Uruguay","Uzbekistan","Venezuela","Vietnam","Zambia","Zimbabwe",
].filter(c => !_mapped.includes(c));

export const COUNTRIES = [..._mapped, ..._rest.sort()];

export const DEFAULT_COUNTRY = "Oman";

/** Returns the list of states for a given country, or [] if unknown. */
export function statesFor(country) {
  return COUNTRY_STATES[country] || [];
}

// ── GST state codes (first 2 digits of a GSTIN) → Indian state name ──
// Mirrors the place-of-supply list used across Customers/Invoices.
export const GST_STATE_BY_CODE = {
  "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
  "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
  "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
  "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
  "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
  "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
  "24": "Gujarat", "25": "Daman and Diu", "26": "Dadra and Nagar Haveli",
  "27": "Maharashtra", "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
  "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
  "35": "Andaman and Nicobar Islands", "36": "Telangana",
  "37": "Andhra Pradesh", "38": "Ladakh",
};

/** Derive the Indian state from a GSTIN's first 2 digits. Returns "" if unknown. */
export function stateFromGstin(gstin) {
  if (!gstin || gstin.length < 2) return "";
  return GST_STATE_BY_CODE[gstin.slice(0, 2)] || "";
}