from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

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
    uvicorn.run(app, host="127.0.0.1", port=8000)