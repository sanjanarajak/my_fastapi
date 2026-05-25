from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import os
import uvicorn

app = FastAPI()

# ---- CORS Configuration ----
# For production, replace ["*"] with your actual frontend URLs, e.g., ["http://localhost:3000"]
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Allows all headers (Content-Type, Authorization, etc.)
)
# ----------------------------

# Matches your frontend payload structure
class MessagePayload(BaseModel):
    message: str

# Aligned mock database: Changed "message" key to "text" to match your UI mapping!
chat_history: List[Dict[str, str]] = [
    {"sender": "bot", "text": "Hello! How can I help you today?"}
]

@app.get("/chat/load-history")
def load_history():
    """Returns the chat history list matching frontend property names."""
    return {"status": "success", "history": chat_history}

@app.post("/chat/message")
def send_message(payload: MessagePayload):
    """Receives a user message, stores it, and returns a response matching the UI."""
    # 1. Save user message to history using 'text'
    chat_history.append({"sender": "user", "text": payload.message})
    
    # 2. Simulate a basic bot reply
    bot_reply = f"Received your message: '{payload.message}'"
    chat_history.append({"sender": "bot", "text": bot_reply})
    
    return {
        "status": "success",
        "user_message": payload.message,
        "reply": bot_reply # Handled dynamically by handleSubmit in ChatWindow
    }

# Fix: Corrected syntax typo (__name__ and __main__) and added dynamic port allocation
if __name__ == "__main__":
    # Pull the port assigned by Railway, default to 8000 for local development
    port = int(os.environ.get("PORT", 8000))
    
    # Force host to 0.0.0.0 to allow Railway's proxy network to connect
    uvicorn.run("main:app", host="0.0.0.0", port=port)