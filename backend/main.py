import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from agent import research_graph

app = FastAPI(title="Deep Research API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws/research")
async def research_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected via WebSocket")
    try:
        data = await websocket.receive_text()
        request = json.loads(data)
        query = request.get("query")
        
        if not query:
            await websocket.send_text(json.dumps({"type": "error", "message": "No query provided"}))
            await websocket.close()
            return
            
        initial_state = {
            "query": query,
            "messages": [],
            "plan": [],
            "current_step_idx": 0,
            "search_results": [],
            "draft_report": "",
            "confidence_score": 0.0,
            "sources": [],
            "status": "starting"
        }
        
        await websocket.send_text(json.dumps({"type": "status", "data": "starting"}))
        
        # Run graph iteratively and stream updates
        async for output in research_graph.astream(initial_state):
            # Output is a dict mapping node_name to state updates
            for node_name, state_update in output.items():
                print(f"--- Node: {node_name} ---")
                
                # Send node status update
                await websocket.send_text(json.dumps({
                    "type": "node_update",
                    "node": node_name,
                    "state": state_update
                }))
                
                # Small delay to simulate processing and let frontend catch up visually
                await asyncio.sleep(0.5)
                
        # Final state sent
        await websocket.send_text(json.dumps({"type": "done"}))
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error during research: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass
        
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
