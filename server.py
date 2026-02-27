print("HYBRID ASSISTANT CLOUD v2 ACTIVE (Facts + Maps + Light AI)")

import os
import requests
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 5000))


# ----------------------------
# HOMEPAGE
# ----------------------------

@app.route("/")
def home():
    return "Dan Assistant Cloud Mode Active"


# ----------------------------
# TOPIC EXTRACTION
# ----------------------------

def extract_topic(question):
    q = question.lower()

    patterns = [
        r"when was (.+)",
        r"who fought in (.+)",
        r"what was (.+)",
        r"why was (.+?) important",
        r"why was (.+)",
        r"where is (.+)",
        r"where was (.+)",
        r"explain (.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return match.group(1).strip(" ?.")

    return question


# ----------------------------
# WIKIPEDIA ENGINE
# ----------------------------

def wikipedia_summary(query):
    headers = {"User-Agent": "DanAssistantCloud/1.0"}

    try:
        topic = extract_topic(query)

        search_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json"
        }

        r = requests.get(search_url, params=params, headers=headers, timeout=5)
        data = r.json()

        if "query" in data and data["query"]["search"]:
            page_title = data["query"]["search"][0]["title"]

            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
            summary_response = requests.get(summary_url, headers=headers, timeout=5)

            if summary_response.status_code == 200:
                return summary_response.json().get("extract", "")

        return ""

    except:
        return ""


# ----------------------------
# MAP ENGINE
# ----------------------------

def geocode_location(query):
    headers = {"User-Agent": "DanAssistantCloud/1.0"}

    try:
        topic = extract_topic(query)

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": topic,
            "format": "json",
            "limit": 1
        }

        r = requests.get(url, params=params, headers=headers, timeout=5)
        data = r.json()

        if data:
            place = data[0]
            return {
                "type": "location",
                "display_name": place["display_name"],
                "latitude": place["lat"],
                "longitude": place["lon"],
                "ios_map_url": f"http://maps.apple.com/?ll={place['lat']},{place['lon']}"
            }

        return None

    except:
        return None


# ----------------------------
# LIGHT REASONING (FREE MODE)
# ----------------------------

def light_reasoning(prompt):
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/google/flan-t5-large",
            json={"inputs": prompt},
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and "generated_text" in result[0]:
                return result[0]["generated_text"]

        return "Cloud reasoning limited. Please refine your question."

    except:
        return "Cloud reasoning currently unavailable."


# ----------------------------
# INTENT DETECTION
# ----------------------------

def detect_intent(message):
    lower = message.lower()

    if lower.startswith("where"):
        return "where"
    if lower.startswith("when"):
        return "fact"
    if lower.startswith("who"):
        return "fact"
    if lower.startswith("what"):
        return "fact"
    if "why" in lower or "explain" in lower:
        return "explain"

    return "general"


# ----------------------------
# CHAT ROUTE
# ----------------------------

@app.route("/chat/<username>", methods=["POST"])
def chat(username):

    user_message = request.json.get("message")

    if not user_message:
        return jsonify({"error": "message required"}), 400

    intent = detect_intent(user_message)

    # MAPS
    if intent == "where":
        location = geocode_location(user_message)
        if location:
            return jsonify(location)

    # FACTS
    if intent in ["fact", "explain"]:
        extract = wikipedia_summary(user_message)
        if extract:
            sentences = extract.split(".")
            clean = ". ".join(sentences[:3]).strip()
            return jsonify({"response": clean})

    # GENERAL REASONING
    answer = light_reasoning(user_message)
    return jsonify({"response": answer})


import os

if __name__ == "__main__":
    print("HYBRID ASSISTANT CLOUD v7 ACTIVE")

    port = int(os.environ.get("PORT", 5001))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
