import swisseph as swe
import datetime
import pytz
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from tabulate import tabulate
import math
from typing import cast

################################################################################
# CONSTANTS AND CONFIGURATION
################################################################################

# Static birth details for MVP
STATIC_PLACE = "Samastipur"
STATIC_BIRTHDATE = "1995-10-09"
STATIC_BIRTHTIME = "8:22"

# Planet constants for Swiss Ephemeris
PLANETS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mars': swe.MARS,
    'Mercury': swe.MERCURY,
    'Jupiter': swe.JUPITER,
    'Venus': swe.VENUS,
    'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE,  # Mean node for Rahu
}

# Vedic zodiac signs (Rashis)
RASHIS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

################################################################################
# UTILITY FUNCTIONS
################################################################################

def normalize_degree(degree: float) -> float:
    """Normalize degree to 0-360 range"""
    return degree % 360

def get_rashi(degree: float) -> str:
    """Convert degree (0-360) to Rashi name using sidereal zodiac"""
    normalized_degree = normalize_degree(degree)
    rashi_index = int(normalized_degree // 30)
    return RASHIS[rashi_index]

def get_degree_within_sign(degree: float) -> float:
    """Get degree within the current sign (0-30 range)"""
    return normalize_degree(degree) % 30

def get_sign_name(degree: float) -> str:
    """Alternative function to get sign name - same as get_rashi"""
    return get_rashi(degree)

################################################################################
# LOCATION AND TIME HANDLING
################################################################################

def get_location_details(place_name: str, birthdate: str, birthtime: str):
    """
    Geocode place name and return location details with timezone
    
    Args:
        place_name: Name of the place (e.g., "Samastipur")
        birthdate: Birth date in YYYY-MM-DD format
        birthtime: Birth time in HH:MM format (24-hour)
    
    Returns:
        tuple: (latitude, longitude, timezone_string, localized_datetime)
    """
    # Geocode the place name to get coordinates
    geolocator = Nominatim(user_agent="vedic_astrology_mvp")
    location = geolocator.geocode(place_name + ", India")  # Adding India for better results
    
    from geopy.location import Location
    location = cast(Location, location)
    
    if not location:
        raise ValueError(f"Could not geocode place: {place_name}")
    
    lat, lon = location.latitude, location.longitude
    
    # Find timezone from coordinates
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lng=lon, lat=lat)
    
    if not timezone_str:
        raise ValueError(f"Could not determine timezone for: {place_name}")
    
    # Parse birth datetime and localize to timezone
    dt_naive = datetime.datetime.strptime(f"{birthdate} {birthtime}", "%Y-%m-%d %H:%M")
    tz = pytz.timezone(timezone_str)
    dt_local = tz.localize(dt_naive)
    
    return lat, lon, timezone_str, dt_local

def get_julian_day(dt_local):
    """
    Convert localized datetime to Julian Day (UT) for Swiss Ephemeris
    
    Args:
        dt_local: Localized datetime object
    
    Returns:
        float: Julian Day in UT
    """
    # Convert to UTC for Julian Day calculation
    ut = dt_local.astimezone(pytz.utc)
    jd_ut = swe.julday(ut.year, ut.month, ut.day, ut.hour + ut.minute / 60.0)
    
    return jd_ut

################################################################################
# PLANETARY CALCULATIONS
################################################################################

def get_planet_positions(jd_ut: float) -> dict:
    """
    Calculate positions of all planets including Rahu and Ketu
    
    Args:
        jd_ut: Julian Day in UT
    
    Returns:
        dict: Planet data with degree, rashi, retrograde, and combustion info
    """
    # Set sidereal mode to Lahiri (Chitrapaksha) ayanamsa
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    planet_data = {}
    sun_degree = None
    
    # Calculate positions for all main planets
    for planet_name, planet_id in PLANETS.items():
        # Set calculation flags for sidereal positions with speed
        flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_SPEED
        
        # Calculate planet position
        xx, retflag = swe.calc_ut(jd_ut, planet_id, flag)
        
        degree = normalize_degree(xx[0])
        rashi = get_rashi(degree)
        retrograde = xx[3] < 0 if len(xx) > 3 else False
        
        planet_data[planet_name] = {
            'degree': degree,
            'rashi': rashi,
            'retrograde': retrograde,
            'combust': False  # Will be calculated after getting Sun's position
        }
        
        # Store Sun's position for combustion calculations
        if planet_name == 'Sun':
            sun_degree = degree
    
    # Calculate Ketu position (always 180° from Rahu)
    rahu_degree = planet_data['Rahu']['degree']
    ketu_degree = normalize_degree(rahu_degree + 180)
    ketu_rashi = get_rashi(ketu_degree)
    
    planet_data['Ketu'] = {
        'degree': ketu_degree,
        'rashi': ketu_rashi,
        'retrograde': True,  # Ketu is always considered retrograde
        'combust': False
    }
    
    # Calculate combustion for planets (within 10° of Sun)
    for planet_name in planet_data:
        if planet_name in ['Sun', 'Rahu', 'Ketu']:
            continue  # These cannot be combust
        
        planet_degree = planet_data[planet_name]['degree']
        # Calculate angular distance from Sun
        angular_distance = abs((planet_degree - sun_degree + 180) % 360 - 180)
        is_combust = angular_distance <= 10
        
        planet_data[planet_name]['combust'] = is_combust
    
    return planet_data

################################################################################
# HOUSE CALCULATIONS
################################################################################

def get_houses(jd_ut: float, lat: float, lon: float):
    """
    Calculate 12 house cusps using Placidus system
    
    Args:
        jd_ut: Julian Day in UT
        lat: Latitude
        lon: Longitude
    
    Returns:
        tuple: (house_cusps_list, ascmc_array)
    """
    # Set sidereal mode for houses
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    # Calculate houses using Placidus system (most common in Vedic astrology)
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'A', swe.FLG_SIDEREAL)
    
    # Handle different cusp array formats
    if len(cusps) == 13:
        house_cusps = list(cusps[1:13])  # Use indices 1-12
    elif len(cusps) == 12:
        house_cusps = list(cusps[0:12])  # Use indices 0-11
    else:
        house_cusps = list(cusps)
    
    return house_cusps, ascmc

def get_house_signs(house_cusps: list) -> list:
    """
    Determine the sign for each house based on actual house cusp degrees
    
    Args:
        house_cusps: List of 12 house cusp degrees
    
    Returns:
        list: Signs for each house (1-12)
    """
    house_signs = []
    
    # Each house sign is determined by where its cusp degree falls in the zodiac
    for cusp_degree in house_cusps:
        normalized_degree = normalize_degree(cusp_degree)
        rashi = get_rashi(normalized_degree)
        house_signs.append(rashi)
    
    return house_signs

def assign_planets_to_houses(planets: dict, house_signs: list) -> dict:
    """
    Assign each planet to its corresponding house based on rashi matching
    
    Args:
        planets: Dictionary of planet data
        house_signs: List of 12 house signs/rashis
    
    Returns:
        dict: Houses (1-12) with their planets
    """
    house_planets = {i: [] for i in range(1, 13)}
    
    for planet_name, planet_data in planets.items():
        planet_rashi = planet_data['rashi']
        
        # Find which house this planet's rashi corresponds to
        for house_num, house_rashi in enumerate(house_signs, 1):
            if planet_rashi == house_rashi:
                house_planets[house_num].append((planet_name, planet_data))
                break
    
    return house_planets

################################################################################
# OUTPUT FORMATTING
################################################################################

def format_planet_info(planet_name: str, planet_data: dict) -> str:
    """
    Format planet information for display
    
    Args:
        planet_name: Name of the planet
        planet_data: Planet data dictionary
    
    Returns:
        str: Formatted planet string with degree and status
    """
    degree_in_sign = get_degree_within_sign(planet_data['degree'])
    sign_name = planet_data['rashi']
    
    # Build status indicators
    status_indicators = []
    if planet_data.get('retrograde'):
        status_indicators.append('R')
    if planet_data.get('combust'):
        status_indicators.append('Combust')
    
    status_str = f" [{', '.join(status_indicators)}]" if status_indicators else ""
    
    return f"{planet_name} ({degree_in_sign:.2f}° {sign_name}){status_str}"

# def create_final_summary_table(planets: dict, house_cusps: list):
#     """
#     Create the final summary table in the requested format:
#     House || Rashi || Planets (With degree)
    
#     Args:
#         planets: Dictionary of planet data
#         house_cusps: List of house cusp degrees
#     """
#     print("\n" + "="*80)
#     print("VEDIC ASTROLOGY CHART SUMMARY")
#     print("="*80)
    
#     # Get house signs and planet assignments
#     house_signs = get_house_signs(house_cusps)
#     house_planets = assign_planets_to_houses(planets, house_cusps)
    
#     # Print table header
#     print("House || Rashi        || Planets (With degree)")
#     print("-" * 80)
    
#     # Print each house with its sign and planets
#     for house_num in range(1, 13):
#         rashi = house_signs[house_num - 1]
#         planets_in_house = house_planets[house_num]
        
#         if planets_in_house:
#             # Format planet information
#             planet_strings = []
#             for planet_name, planet_data in planets_in_house:
#                 planet_info = format_planet_info(planet_name, planet_data)
#                 planet_strings.append(planet_info)
            
#             planets_display = ", ".join(planet_strings)
#         else:
#             planets_display = "-"
        
#         print(f"{house_num:5} || {rashi:<11} || {planets_display}")
    
#     print("="*80)

################################################################################
# ADDITIONAL OUTPUT FUNCTIONS
################################################################################

def print_house_rashi_mapping(house_signs: list):
    """Print simple house to rashi mapping"""
    print("\n" + "-"*40)
    print("HOUSE TO RASHI MAPPING")
    print("-"*40)
    
    for i, rashi in enumerate(house_signs, 1):
        print(f"House {i:2} -- {rashi}")

def print_rashi_planet_distribution(planets: dict, house_signs: list):
    """Print planets distributed by rashi with house numbers"""
    print("\n" + "-"*40)
    print("PLANETS IN EACH RASHI")
    print("-"*40)
    
    # Group planets by rashi
    rashi_planets = {rashi: [] for rashi in RASHIS}
    
    for planet_name, planet_data in planets.items():
        rashi = planet_data['rashi']
        degree_in_sign = get_degree_within_sign(planet_data['degree'])
        rashi_planets[rashi].append((planet_name, degree_in_sign))
    
    # Create rashi to house mapping
    rashi_to_house = {}
    for house_num, rashi in enumerate(house_signs, 1):
        rashi_to_house[rashi] = house_num
    
    # Print each rashi with its planets and house number in ascending house order
    for house_num in range(1, 13):
        rashi = house_signs[house_num - 1]
        planet_list = rashi_planets[rashi]
        
        if planet_list:
            planet_strings = [f"{p} ({deg:.2f}°)" for p, deg in planet_list]
            planets_display = ", ".join(planet_strings)
        else:
            planets_display = "-"
        
        print(f"{rashi:<12} (House {house_num:2}): {planets_display}")

def print_house_summary_table(planets: dict, house_cusps: list):
    """
    Print the main summary table: House || Rashi || Planet (with degree)
    
    Args:
        planets: Dictionary of planet data
        house_cusps: List of house cusp degrees
    """
    print("\n" + "="*80)
    print("VEDIC ASTROLOGY CHART SUMMARY")
    print("="*80)
    
    # Get house signs and planet assignments
    house_signs = get_house_signs(house_cusps)
    house_planets = assign_planets_to_houses(planets, house_cusps)
    
    # Print table header
    print("House || Rashi        || Planet (with degree)")
    print("-" * 80)
    
    # Print each house with its sign and planets
    for house_num in range(1, 13):
        rashi = house_signs[house_num - 1]
        planets_in_house = house_planets[house_num]
        
        if planets_in_house:
            # Format planet information
            planet_strings = []
            for planet_name, planet_data in planets_in_house:
                planet_info = format_planet_info(planet_name, planet_data)
                planet_strings.append(planet_info)
            
            planets_display = ", ".join(planet_strings)
        else:
            planets_display = "-"
        
        print(f"{house_num:5} || {rashi:<11} || {planets_display}")
    
    print("="*80)

################################################################################
# MAIN EXECUTION FUNCTION
################################################################################

def generate_kundli_data(birth_data=None):
    """
    Generate Vedic astrology calculations and return structured data
    
    Args:
        birth_data: Dictionary with keys 'ddd', 'mmm', 'yyyy', 'hh', 'mm', 'place'
                   If None, uses static values
    
    Returns:
        dict: Structured kundli data
    """
    try:
        # Use provided data or fall back to static values
        if birth_data:
            place = birth_data.get('place', STATIC_PLACE)
            day = str(birth_data.get('ddd', '09')).zfill(2)
            month = str(birth_data.get('mmm', '10')).zfill(2)
            year = str(birth_data.get('yyyy', '1995'))
            hour = str(birth_data.get('hh', '8')).zfill(2)
            minute = str(birth_data.get('mm', '22')).zfill(2)
            
            birthdate = f"{year}-{month}-{day}"
            birthtime = f"{hour}:{minute}"
        else:
            place = STATIC_PLACE
            birthdate = STATIC_BIRTHDATE
            birthtime = STATIC_BIRTHTIME
        
        # Step 1: Get location details and timezone
        lat, lon, timezone_str, dt_local = get_location_details(
            place, birthdate, birthtime
        )
        
        # Step 2: Calculate Julian Day for Swiss Ephemeris
        jd_ut = get_julian_day(dt_local)
        
        # Step 3: Calculate planetary positions
        planets = get_planet_positions(jd_ut)
        
        # Step 4: Calculate house cusps
        house_cusps, ascmc = get_houses(jd_ut, lat, lon)
        
        # Step 5: Generate structured data
        house_signs = get_house_signs(house_cusps)
        house_planets = assign_planets_to_houses(planets, house_cusps)
        
        # Create structured response
        result = {
            "birth_details": {
                "place": place,
                "date": birthdate,
                "time": birthtime,
                "timezone": timezone_str,
                "coordinates": {"latitude": lat, "longitude": lon}
            },
            "houses": [],
            "planets": {},
            "rashis": {}
        }
        
        # Build houses data
        for house_num in range(1, 13):
            rashi = house_signs[house_num - 1]
            planets_in_house = house_planets[house_num]
            
            house_data = {
                "house_number": house_num,
                "rashi": rashi,
                "planets": []
            }
            
            for planet_name, planet_data in planets_in_house:
                degree_in_sign = get_degree_within_sign(planet_data['degree'])
                planet_info = {
                    "name": planet_name,
                    "degree": round(degree_in_sign, 2),
                    "retrograde": planet_data.get('retrograde', False),
                    "combust": planet_data.get('combust', False)
                }
                house_data["planets"].append(planet_info)
            
            result["houses"].append(house_data)
        
        # Build planets data
        for planet_name, planet_data in planets.items():
            result["planets"][planet_name] = {
                "degree": round(planet_data['degree'], 2),
                "rashi": planet_data['rashi'],
                "degree_in_sign": round(get_degree_within_sign(planet_data['degree']), 2),
                "retrograde": planet_data.get('retrograde', False),
                "combust": planet_data.get('combust', False)
            }
        
        # Build rashis data
        for house_num in range(1, 13):
            rashi = house_signs[house_num - 1]
            planets_in_rashi = []
            
            for planet_name, planet_data in planets.items():
                if planet_data['rashi'] == rashi:
                    degree_in_sign = get_degree_within_sign(planet_data['degree'])
                    planets_in_rashi.append({
                        "name": planet_name,
                        "degree": round(degree_in_sign, 2)
                    })
            
            result["rashis"][rashi] = {
                "house_number": house_num,
                "planets": planets_in_rashi
            }
        
        return result
        
    except Exception as e:
        return {
            "error": f"Calculation failed: {str(e)}",
            "birth_details": birth_data if birth_data else {}
        }

def generate_clean_json_output(birth_data=None):
    """
    Generate clean JSON output optimized for LLM processing
    
    Args:
        birth_data: Dictionary with keys 'ddd', 'mmm', 'yyyy', 'hh', 'mm', 'place'
                   If None, uses static values
    
    Returns:
        dict: Clean JSON structure with LAGNA and house information
    """
    try:
        # Use provided data or fall back to static values
        if birth_data:
            place = birth_data.get('place', STATIC_PLACE)
            day = str(birth_data.get('ddd', '09')).zfill(2)
            month = str(birth_data.get('mmm', '10')).zfill(2)
            year = str(birth_data.get('yyyy', '1995'))
            hour = str(birth_data.get('hh', '8')).zfill(2)
            minute = str(birth_data.get('mm', '22')).zfill(2)
            
            birthdate = f"{year}-{month}-{day}"
            birthtime = f"{hour}:{minute}"
            date_display = f"{day}-{month}-{year}"
        else:
            place = STATIC_PLACE
            birthdate = STATIC_BIRTHDATE
            birthtime = STATIC_BIRTHTIME
            date_display = f"{STATIC_BIRTHDATE.split('-')[2]}-{STATIC_BIRTHDATE.split('-')[1]}-{STATIC_BIRTHDATE.split('-')[0]}"
        
        # Get location details and calculate positions
        lat, lon, timezone_str, dt_local = get_location_details(
            place, birthdate, birthtime
        )
        
        jd_ut = get_julian_day(dt_local)
        planets = get_planet_positions(jd_ut)
        house_cusps, ascmc = get_houses(jd_ut, lat, lon)
        house_signs = get_house_signs(house_cusps)
        house_planets = assign_planets_to_houses(planets, house_signs)
        
        # Create clean JSON structure
        result = {
            "birth_info": {
                "date": date_display,
                "time": birthtime,
                "place": place,
                "coordinates": f"{lat:.4f}°, {lon:.4f}°"
            },
            "lagna": {
                "description": "LAGNA represents the Ascendant or 1st House, which is the zodiac sign rising on the eastern horizon at the time of birth. It determines the overall personality and physical appearance.",
                "rashi": house_signs[0]
            },
            "houses": []
        }
        
        # Build houses data
        for house_num in range(1, 13):
            rashi = house_signs[house_num - 1]
            planets_in_house = house_planets[house_num]
            
            # Format planets with degrees
            if planets_in_house:
                planet_strings = []
                for planet_name, planet_data in planets_in_house:
                    degree_in_sign = get_degree_within_sign(planet_data['degree'])
                    
                    # Add status indicators
                    status_indicators = []
                    if planet_data.get('retrograde'):
                        status_indicators.append('R')
                    if planet_data.get('combust'):
                        status_indicators.append('Combust')
                    
                    status_str = f" [{', '.join(status_indicators)}]" if status_indicators else ""
                    planet_string = f"{planet_name}({degree_in_sign:.2f}deg){status_str}"
                    planet_strings.append(planet_string)
                
                planets_display = ", ".join(planet_strings)
            else:
                planets_display = ""
            
            house_data = {
                "house_number": house_num,
                "rashi": rashi,
                "planets": planets_display
            }
            
            result["houses"].append(house_data)
        
        return result
        
    except Exception as e:
        return {
            "error": "Miscalculation",
            "birth_info": {
                "date": "",
                "time": "",
                "place": "",
                "coordinates": ""
            },
            "lagna": {
                "description": "Miscalculation",
                "rashi": ""
            },
            "houses": []
        }

def display_json_output(birth_data=None, test_case_num=None):
    """
    Display JSON output for viewing
    
    Args:
        birth_data: Dictionary with keys 'ddd', 'mmm', 'yyyy', 'hh', 'mm', 'place'
                   If None, uses static values
        test_case_num: Test case number for header
    """
    import json
    
    if test_case_num:
        print(f"\nTest case #{test_case_num} - JSON Output")
        print("=" * 50)
    else:
        print(f"\nKundli JSON Output")
        print("=" * 30)
    
    try:
        result = generate_clean_json_output(birth_data)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error generating JSON: {e}")

def display_table_output(birth_data=None, test_case_num=None):
    """
    Display clean formatted output with custom birth data
    
    Args:
        birth_data: Dictionary with keys 'ddd', 'mmm', 'yyyy', 'hh', 'mm', 'place'
                   If None, uses static values
        test_case_num: Test case number for header
    """
    try:
        # Use provided data or fall back to static values
        if birth_data:
            place = birth_data.get('place', STATIC_PLACE)
            day = str(birth_data.get('ddd', '09')).zfill(2)
            month = str(birth_data.get('mmm', '10')).zfill(2)
            year = str(birth_data.get('yyyy', '1995'))
            hour = str(birth_data.get('hh', '8')).zfill(2)
            minute = str(birth_data.get('mm', '22')).zfill(2)
            
            birthdate = f"{year}-{month}-{day}"
            birthtime = f"{hour}:{minute}"
            date_display = f"{day}-{month}-{year}"
        else:
            place = STATIC_PLACE
            birthdate = STATIC_BIRTHDATE
            birthtime = STATIC_BIRTHTIME
            date_display = f"{STATIC_BIRTHDATE.split('-')[2]}-{STATIC_BIRTHDATE.split('-')[1]}-{STATIC_BIRTHDATE.split('-')[0]}"
        
        # Get location details and timezone
        lat, lon, timezone_str, dt_local = get_location_details(
            place, birthdate, birthtime
        )
        
        # Calculate positions
        jd_ut = get_julian_day(dt_local)
        planets = get_planet_positions(jd_ut)
        house_cusps, ascmc = get_houses(jd_ut, lat, lon)
        house_signs = get_house_signs(house_cusps)
        house_planets = assign_planets_to_houses(planets, house_signs)
        
        # Display clean output
        if test_case_num:
            print(f"\nTest case #{test_case_num}")
        else:
            print(f"\nKundli Analysis")
            
        print(f"{date_display} || {birthtime} || {place} ({lat:.4f}°, {lon:.4f}°)")
        
        print(f"\nRashi || House")
        print("-" * 20)
        for i, rashi in enumerate(house_signs, 1):
            print(f"{rashi:<12} || {i:2}")
        
        print(f"\nPlanet || Rashi")
        print("-" * 20)
        for planet_name, planet_data in planets.items():
            print(f"{planet_name:<8} || {planet_data['rashi']}")
        
        print(f"\nVedic Astro Summary")
        print("=" * 80)
        print("House || Rashi        || Planet (with degree)")
        print("-" * 80)
        
        for house_num in range(1, 13):
            rashi = house_signs[house_num - 1]
            planets_in_house = house_planets[house_num]
            
            if planets_in_house:
                planet_strings = []
                for planet_name, planet_data in planets_in_house:
                    degree_in_sign = get_degree_within_sign(planet_data['degree'])
                    status_indicators = []
                    if planet_data.get('retrograde'):
                        status_indicators.append('R')
                    if planet_data.get('combust'):
                        status_indicators.append('Combust')
                    
                    status_str = f" [{', '.join(status_indicators)}]" if status_indicators else ""
                    planet_info = f"{planet_name} ({degree_in_sign:.2f}° {planet_data['rashi']}){status_str}"
                    planet_strings.append(planet_info)
                
                planets_display = ", ".join(planet_strings)
            else:
                planets_display = "-"
            
            print(f"{house_num:5} || {rashi:<11} || {planets_display}")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Calculation failed: {str(e)}")
        import traceback
        traceback.print_exc()

def main(birth_data=None):
    """
    Main function to execute Vedic astrology calculations
    Can accept birth_data for API calls or use static values for standalone execution
    """
    if birth_data:
        # When called from API, return clean JSON optimized for LLM processing
        return generate_clean_json_output(birth_data)
    else:
        # When called standalone, print the traditional output
        display_table_output()

################################################################################
# PROGRAM ENTRY POINT
################################################################################

if __name__ == "__main__":
    main()