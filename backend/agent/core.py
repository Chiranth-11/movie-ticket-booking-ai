from typing import Dict, Any, Optional
from ..models import ChatRequest, ChatResponse, ToolCallRecord
from .llm_provider import AutonomousReasoningEngine
from .tools import AVAILABLE_TOOLS_SPECS

class CineAgent:
    def __init__(self):
        # In-memory session store: session_id -> state dict
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "active_movie_id": None,
                "active_showtime_id": None,
                "selected_seats": [],
                "promo_code": None,
                "customer_name": "Chiranth C Gutthi",
                "customer_email": "chiranthgutthi@gmail.com",
                "history": []
            }
        return self.sessions[session_id]

    def chat(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or "default_session"
        session_state = self.get_or_create_session(session_id)

        # Merge incoming request hints
        if request.current_movie_id:
            session_state["active_movie_id"] = request.current_movie_id
        if request.current_showtime_id:
            session_state["active_showtime_id"] = request.current_showtime_id

        # Process turn using autonomous ReAct agentic engine
        reply, tool_records, ui_action = AutonomousReasoningEngine.process_turn(
            message=request.message,
            session_state=session_state
        )

        # Append to history
        session_state["history"].append({"role": "user", "content": request.message})
        session_state["history"].append({
            "role": "assistant",
            "content": reply,
            "tool_calls": [t.model_dump() for t in tool_records]
        })

        # Sanitize session state for JSON return
        clean_state = {
            "active_movie_id": session_state.get("active_movie_id"),
            "active_showtime_id": session_state.get("active_showtime_id"),
            "selected_seats": session_state.get("selected_seats", []),
            "promo_code": session_state.get("promo_code"),
            "customer_name": session_state.get("customer_name")
        }

        return ChatResponse(
            reply=reply,
            session_id=session_id,
            tool_calls=tool_records,
            ui_action=ui_action,
            session_state=clean_state
        )

# Global singleton
agent_instance = CineAgent()
