from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__, static_folder=".", static_url_path="")

# -----------------------------
# CONFIG
# -----------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "mistralai/mistral-7b-instruct"  # Stable + inexpensive

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health")
def health():
    return {"status": "ok"}

# -----------------------------
# HOMEPAGE
# -----------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# -----------------------------
# SAFETY FILTER
# -----------------------------
def is_blocked(message):
    blocked_terms = [
        "rob a bank",
        "kill someone",
        "bomb",
        "terrorist",
        "child abuse",
        "how to make explosives"
    ]
    lower = message.lower()
    return any(term in lower for term in blocked_terms)

# -----------------------------
# CHAT ENDPOINT
# -----------------------------
@app.route("/chat/dan", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Message required"}), 400

    user_message = data["message"]

    if is_blocked(user_message):
        return jsonify({
            "response": "I cannot assist with illegal or harmful activities."
        })

    if not OPENROUTER_API_KEY:
        return jsonify({
            "response": "AI engine not configured."
        }), 500

    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a structured, private assistant platform. Provide accurate, concise, helpful answers. Refuse illegal or harmful requests."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        result = response.json()

        if "choices" not in result:
            return jsonify({
                "response": "Model response error."
            }), 500

        assistant_reply = result["choices"][0]["message"]["content"]

        return jsonify({"response": assistant_reply})

    except Exception as e:
        return jsonify({
            "response": "Server error occurred."
        }), 500


# -----------------------------
# LOCAL RUN (not used in Railway)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
