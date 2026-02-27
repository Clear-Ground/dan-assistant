from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder=".", static_url_path="")

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
# CHAT ENDPOINT
# -----------------------------
@app.route("/chat/dan", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "message required"}), 400

    user_message = data["message"]

    # Simple structured response (safe baseline)
    response = f"You said: {user_message}"

    return jsonify({"response": response})


# -----------------------------
# RUN (local only)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
