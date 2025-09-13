CANADIAN_AIRPORTS = {
    # Major International Airports
    'YYZ': 'Toronto Pearson International Airport',
    'YVR': 'Vancouver International Airport',
    'YUL': 'Montreal-Pierre Elliott Trudeau International Airport',
    'YYC': 'Calgary International Airport',
    'YWG': 'Winnipeg James Armstrong Richardson International Airport',
    'YOW': 'Ottawa Macdonald-Cartier International Airport',
    'YHZ': 'Halifax Stanfield International Airport',
    'YEG': 'Edmonton International Airport',
    'YQB': 'Quebec City Jean Lesage International Airport',
    'YXE': 'Saskatoon John G. Diefenbaker International Airport',
    
    # Regional Airports
    'YYJ': 'Victoria International Airport',
    'YKF': 'Kitchener/Waterloo Regional Airport',
    'YHM': 'John C. Munro Hamilton International Airport',
    'YFB': 'Iqaluit Airport',
    'YXY': 'Whitehorse International Airport',
    'YZF': 'Yellowknife Airport',
    'YQR': 'Regina International Airport',
    'YQT': 'Thunder Bay International Airport',
    'YSJ': 'Saint John Airport',
    'YFC': 'Fredericton International Airport',
    'YQM': 'Greater Moncton Roméo LeBlanc International Airport',
    'YQX': 'Gander International Airport',
    'YYT': "St. John's International Airport",
    'YXU': 'London International Airport',
    'YKA': 'Kamloops Airport',
    'YPG': 'Prince George Airport',
    'YQU': 'Grande Prairie Airport',
    'YMM': 'Fort McMurray Airport',
    'YLW': 'Kelowna International Airport',
    'YXS': 'Prince Albert Glass Field',
    'YBR': 'Brandon Municipal Airport',
    'YTS': 'Timmins Victor M. Power Airport',
    'YSB': 'Sudbury Airport',
    'YAM': 'Sault Ste. Marie Airport',
    'YQK': 'Kenora Airport',
    'YZP': 'Sandspit Airport',
    'YCD': 'Nanaimo Airport',
    'YCA': 'Courtenay Airfield',
    'YPW': 'Powell River Airport',
    'YXJ': 'Fort St. John Airport',
    'YDQ': 'Dawson Creek Regional Airport',
    'YFO': 'Flin Flon Airport',
    'YTH': 'Thompson Airport',
    'YCG': 'Castlegar/West Kootenay Regional Airport',
    'YXC': 'Cranbrook Airport',
    
    # Northern and Remote Airports
    'YUX': 'Hall Beach Airport',
    'YFB': 'Iqaluit Airport',
    'YRT': 'Rankin Inlet Airport',
    'YBK': 'Baker Lake Airport',
    'YGZ': 'Grise Fiord Airport',
    'YEV': 'Inuvik Mike Zubko Airport',
    'YAT': 'Attawapiskat Airport',
    'YMO': 'Moosonee Airport',
    'YPH': 'Inukjuak Airport',
    'YWP': 'Webequie Airport',
    'YHO': 'Hopedale Airport',
    'YHR': 'Happy Valley-Goose Bay Airport',
    'YER': 'Fort Severn Airport',
    'YZS': 'Coral Harbour Airport',
}


def is_canadian_airport(airport_code: str) -> bool:
    """Check if an airport code is a Canadian airport."""
    return airport_code.upper() in CANADIAN_AIRPORTS


def get_canadian_airport_name(airport_code: str) -> str:
    """Get the full name of a Canadian airport."""
    return CANADIAN_AIRPORTS.get(airport_code.upper(), "Unknown Airport")