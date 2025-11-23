import requests

USER_AGENT = "aku22ainds@cmrit.ac.in"


def geocode_place(place_name: str):
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place_name,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": USER_AGENT
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
    except requests.RequestException as e:
        print("Error contacting Nominatim:", e)
        return None

    if response.status_code != 200:
        print("Nominatim returned status:", response.status_code)
        print("Response (first 200 chars):", response.text[:200])
        return None

    try:
        data = response.json()
    except ValueError:
        print("Could not decode JSON from Nominatim.")
        print("Response (first 200 chars):", response.text[:200])
        return None

    if not data:
        return None

    first = data[0]
    lat = float(first["lat"])
    lon = float(first["lon"])
    display_name = first.get("display_name", place_name)

    return {
        "lat": lat,
        "lon": lon,
        "display_name": display_name
    }


def get_weather_for_coordinates(lat: float, lon: float):
   
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "hourly": "precipitation_probability"
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    if "current_weather" not in data:
        return None

    current_temp = data["current_weather"].get("temperature")

    rain_chance = None
    hourly = data.get("hourly", {})
    probs = hourly.get("precipitation_probability")
    if probs and len(probs) > 0:
        rain_chance = probs[0]

    return {
        "temperature": current_temp,
        "rain_chance": rain_chance
    }


def weather_agent(place_name: str):
   
    geo = geocode_place(place_name)
    if geo is None:
        return {
            "error": True,
            "message": "I don't know if this place exists."
        }

    weather = get_weather_for_coordinates(geo["lat"], geo["lon"])
    if weather is None:
        return {
            "error": True,
            "message": "I couldn't fetch weather data right now."
        }

    return {
        "error": False,
        "place_name": geo["display_name"],
        "temperature": weather["temperature"],
        "rain_chance": weather["rain_chance"]
    }


def is_valid_tourist_place(tags: dict) -> bool:
    
    tourism_tags = [
        "attraction",
        "museum",
        "gallery",
        "theme_park",
        "zoo",
        "viewpoint",
        "park",
        "monument",
        "heritage"
    ]

    bad_words = [
        "hotel", "lodge", "residency", "resort", "inn",
        "guest", "pg", "mens pg", "ladies pg", "restaurant",
        "bar", "cafe", "shop"
    ]

    name = tags.get("name", "").lower()

    # Remove obvious non-tourist names
    for bad in bad_words:
        if bad in name:
            return False

    # Keep only things tagged as real tourism objects
    if "tourism" in tags and tags["tourism"] in tourism_tags:
        return True

    # Also keep parks if tagged as leisure=park
    if tags.get("leisure") == "park":
        return True

    return False


def get_places_for_coordinates(lat: float, lon: float, limit: int = 5):
    
    url = "https://overpass-api.de/api/interpreter"

    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["tourism"](around:5000,{lat},{lon});
      way["tourism"](around:5000,{lat},{lon});
      relation["tourism"](around:5000,{lat},{lon});
    );
    out center;
    """

    try:
        response = requests.post(url, data=overpass_query, timeout=30)
    except requests.RequestException as e:
        print("Overpass API request error:", e)
        return None

    if response.status_code != 200:
        print("Overpass status:", response.status_code)
        print("Response:", response.text[:200])
        return None

    try:
        data = response.json()
    except ValueError:
        print("Could not decode JSON from Overpass")
        print("Response:", response.text[:200])
        return None

    elements = data.get("elements", [])
    places = []

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")

        if not name:
            continue

        # filter out non-tourist places
        if not is_valid_tourist_place(tags):
            continue

        places.append(name)

        if len(places) >= limit:
            break

    # fallback: if filtering removed everything but we still have some named elements
    if not places:
        raw_places = [el["tags"]["name"] for el in elements if "tags" in el and "name" in el["tags"]]
        return raw_places[:limit]

    return places


def places_agent(place_name: str):

    geo = geocode_place(place_name)
    if geo is None:
        return {
            "error": True,
            "message": "I don't know if this place exists."
        }

    places = get_places_for_coordinates(geo["lat"], geo["lon"], limit=5)

    if not places:
        return {
            "error": True,
            "message": f"I couldn't find popular tourist places near {geo['display_name']}."
        }

    return {
        "error": False,
        "place_name": geo["display_name"],
        "places": places
    }


def extract_place(user_input: str) -> str | None:

    text = user_input
    lower = text.lower()

    if "to " in lower:
        index = lower.index("to ") + len("to ")
        after_to = text[index:].strip()

        # Stop at comma, question mark, or full stop
        for sep in [",", "?", "."]:
            after_to = after_to.split(sep)[0]

        place = after_to.strip()
        if place:
            return place

    return None


def detect_intents(user_input: str):

    text = user_input.lower()

    wants_weather = any(word in text for word in ["temperature", "weather", "hot", "cold"])
    wants_places = any(word in text for word in ["places", "visit", "trip", "plan", "go"])

    return {
        "weather": wants_weather,
        "places": wants_places
    }


def tourism_parent_agent(user_input: str) -> str:

    place = extract_place(user_input)
    if not place:
        return "I couldn't understand which place you want to go. Please type clearly."

    intents = detect_intents(user_input)
    wants_weather = intents["weather"]
    wants_places = intents["places"]

    # Default to places if nothing detected
    if not wants_weather and not wants_places:
        wants_places = True

    weather_result = None
    places_result = None

    if wants_weather:
        weather_result = weather_agent(place)

    if wants_places:
        places_result = places_agent(place)

    # Handle non-existent place from any agent
    if weather_result and weather_result.get("error") and "exists" in weather_result["message"]:
        return weather_result["message"]

    if places_result and places_result.get("error") and "exists" in places_result["message"]:
        return places_result["message"]

    parts = []

    # Weather text
    if wants_weather and weather_result:
        if weather_result["error"]:
            parts.append(weather_result["message"])
        else:
            temp = weather_result["temperature"]
            rain = weather_result["rain_chance"]
            rain_text = f" with a chance of {rain}% to rain" if rain is not None else ""
            parts.append(f"In {place} it's currently {temp}°C{rain_text}.")

    # Places text
    if wants_places and places_result:
        if places_result["error"]:
            parts.append(places_result["message"])
        else:
            places_list = "\n".join(places_result["places"])
            if wants_weather:
                parts.append(f"And these are the places you can go:\n{places_list}")
            else:
                parts.append(f"In {place} these are the places you can go,\n{places_list}")

    return " ".join(parts)


if __name__ == "__main__":
    print("Tourism AI Agent Activated! Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("AI: Goodbye! Have a nice day 😊")
            break

        response = tourism_parent_agent(user_input)
        print("AI:", response)
