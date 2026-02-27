print("HYBRID ASSISTANT v7 ACTIVE (Mobile UI + PWA Ready)")

import requests
import re
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "llama3"


# ----------------------------
# HOMEPAGE (Mobile UI)
# ----------------------------

@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dan Assistant</title>
<link rel="manifest" href="/manifest.json">
<style>
body { font-family: -apple-system; margin: 0; background:#111; color:#fff; }
header { padding:15px; text-align:center; font-weight:bold; background:#1e1e1e; }
#chat { padding:15px; height:70vh; overflow-y:auto; }
.message { margin-bottom:10px; }
.user { color:#4da6ff; }
.assistant { color:#7CFC00; }
input { width:75%; padding:10px; border:none; border-radius:5px; }
button { width:20%; padding:10px; border:none; border-radius:5px; background:#4da6ff; color:white; }
footer { padding:10px; background:#1e1e1e; display:flex; gap:5px; }
</style>
</head>
<body>

<header>Dan Assistant</header>

<div id="chat"></div>

<footer>
<input id="input" placeholder="Ask something..." />
<button onclick="send()">Send</button>
</footer>

<script>
async function send() {
    const input = document.getElementById("input");
    const chat = document.getElementById("chat");

    const userText = input.value;
    if (!userText) return;

    chat.innerHTML += `<div class="message user">You: ${userText}</div>`;
    input.value = "";

    const response = await fetch("/chat/dan", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: userText})
    });

    const data = await response.json();

    if (data.response) {
        chat.innerHTML += `<div class="message assistant">Assistant: ${data.response}</div>`;
    } else if (data.display_name) {
        chat.innerHTML += `<div class="message assistant">Location: ${data.display_name}<br>
        <a href="${data.ios_map_url}" target="_blank">Open in Maps</a></div>`;
    }

    chat.scrollTop = chat.scrollHeight;
}

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
}
</script>

</body>
</html>
"""


# ----------------------------
# PWA FILES
# ----------------------------

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Dan Assistant",
        "short_name": "Assistant",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#111111",
        "theme_color": "#111111",
        "icons": []
    })


@app.route("/sw.js")
def service_worker():
    js = """
self.addEventListener('install', function(e) {
  self.skipWaiting();
});
self.addEventListener('fetch', function(event) {});
"""
    return Response(js, mimetype="application/javascript")


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
# WIKIPEDIA
# ----------------------------

def wikipedia_summary(query):
    headers = {"User-Agent": "DanAssistant/1.0"}
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


def extract_date(text):
    match = re.search(r"\b\d{1,2}\s\w+\s\d{4}\b", text)
    return match.group(0) if match else None


def extract_forces(text):
    match = re.search(r"fought between (.+?)\.", text)
    return match.group(1) if match else None


def first_n_sentences(text, n=3):
    sentences = text.split(".")
    selected = sentences[:n]
    cleaned = [s.strip() for s in selected if s.strip()]
    return ". ".join(cleaned) + "."


# ----------------------------
# MAP ENGINE
# ----------------------------

def geocode_location(query):
    headers = {"User-Agent": "DanAssistant/1.0"}
    try:
        topic = extract_topic(query)
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": topic, "format": "json", "limit": 1}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        data = r.json()

        if data:
            place = data[0]
            return {
                "display_name": place["display_name"],
                "ios_map_url": f"http://maps.apple.com/?ll={place['lat']},{place['lon']}"
            }
        return None
    except:
        return None


# ----------------------------
# MODEL
# ----------------------------

def call_model(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3}
        }
    )
    return response.json().get("response", "").strip()


def detect_intent(message):
    lower = message.lower()
    if lower.startswith("when"): return "when"
    if lower.startswith("who"): return "who"
    if lower.startswith("what"): return "what"
    if lower.startswith("where"): return "where"
    if "why" in lower or "important" in lower or "explain" in lower:
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

    if intent == "where":
        location_data = geocode_location(user_message)
        if location_data:
            return jsonify(location_data)

    if intent in ["when", "who", "what", "explain"]:
        extract = wikipedia_summary(user_message)
        if extract:
            date = extract_date(extract)
            forces = extract_forces(extract)
            first_sentence = extract.split(".")[0] + "."
            three_sentences = first_n_sentences(extract, 3)

            if intent == "when" and date:
                return jsonify({"response": f"It took place on {date}. {first_sentence}"})
            if intent == "who" and forces:
                return jsonify({"response": f"It was fought between {forces}."})
            if intent == "what":
                return jsonify({"response": first_sentence})
            if intent == "explain":
                return jsonify({"response": three_sentences})

    general_prompt = f"You are a private offline assistant. Be concise.\nUser: {user_message}\nAssistant:"
    answer = call_model(general_prompt)
    return jsonify({"response": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)