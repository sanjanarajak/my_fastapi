from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)