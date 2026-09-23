"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import json
import os
import uuid

import google.auth
import google.auth.transport.requests
from google.protobuf.json_format import MessageToDict, ParseDict
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageRequest,
    TaskArtifactUpdateEvent,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/449481897749/locations/us-east1/reasoningEngines/2470129837612728320",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


from google.protobuf.json_format import ParseDict

async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        data = resp.json()

        if hasattr(AgentCard, "model_validate"):
            try:
                card = AgentCard.model_validate(data)
            except Exception:
                card = AgentCard(
                    name=data.get("name", "simple_agent"),
                    description=data.get("description", "An ADK Agent"),
                    version=data.get("version", "0.1.0"),
                    url=A2A_BASE,
                    capabilities=data.get("capabilities", {}),
                    default_input_modes=data.get("defaultInputModes", ["text/plain"]),
                    default_output_modes=data.get("defaultOutputModes", ["text/plain"]),
                    skills=data.get("skills", []),
                )
        else:
            try:
                card = ParseDict(data, AgentCard(), ignore_unknown_fields=True)
            except Exception:
                card = AgentCard()
            if hasattr(card, "supported_interfaces"):
                if not card.supported_interfaces:
                    iface = card.supported_interfaces.add()
                    iface.url = A2A_BASE
                else:
                    for iface in card.supported_interfaces:
                        iface.url = A2A_BASE
        _card = card
    return _card


def _extract_parts_from_artifact(artifact) -> list[dict]:
    out: list[dict] = []
    if not artifact:
        return out

    if isinstance(artifact, dict):
        artifact_dict = artifact
    elif hasattr(artifact, "model_dump"):
        artifact_dict = artifact.model_dump(exclude_none=True)
    elif hasattr(artifact, "DESCRIPTOR"):
        try:
            artifact_dict = MessageToDict(artifact)
        except Exception:
            artifact_dict = {}
    elif hasattr(artifact, "__dict__"):
        artifact_dict = getattr(artifact, "__dict__", {})
    else:
        artifact_dict = {}

    for part in artifact_dict.get("parts", []):
        if "text" in part and part["text"]:
            out.append({"kind": "text", "text": part["text"]})
        elif "data" in part:
            data_val = part["data"]
            if isinstance(data_val, dict):
                inner_data = data_val.get("data", data_val)
                if isinstance(inner_data, str):
                    try:
                        inner_data = json.loads(inner_data)
                    except Exception:
                        pass

                if isinstance(inner_data, dict) and any(k in inner_data for k in ("beginRendering", "surfaceUpdate")):
                    out.append({"kind": "a2ui", "data": inner_data})
                elif "a2ui_datapart_json" in data_val:
                    try:
                        parsed_a2ui = json.loads(data_val["a2ui_datapart_json"])
                        out.append({"kind": "a2ui", "data": parsed_a2ui})
                    except Exception:
                        out.append({"kind": "a2ui", "data": data_val["a2ui_datapart_json"]})
        elif "file" in part:
            file_obj = part["file"]
            uri = file_obj.get("uri") if isinstance(file_obj, dict) else getattr(file_obj, "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(ClientConfig(httpx_client=client))
        a2a_client = factory.create(card)

        user_role = getattr(Role, "ROLE_USER", getattr(Role, "user", None))
        part_obj = Part(text=message)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=user_role,
            parts=[part_obj],
            context_id=_contexts.get(user_id),
        )
        send_payload = msg
        try:
            smr = SendMessageRequest()
            if hasattr(smr, "message") and hasattr(smr.message, "CopyFrom"):
                smr.message.CopyFrom(msg)
                send_payload = smr
        except Exception:
            send_payload = msg

        async for event in a2a_client.send_message(send_payload):
            # Save context_id if set
            if hasattr(event, "task") and event.task.context_id:
                _contexts[user_id] = event.task.context_id
            elif hasattr(event, "status_update") and event.status_update.context_id:
                _contexts[user_id] = event.status_update.context_id
            elif hasattr(event, "artifact_update") and event.artifact_update.context_id:
                _contexts[user_id] = event.artifact_update.context_id

            if hasattr(event, "HasField") and event.HasField("artifact_update"):
                extracted = _extract_parts_from_artifact(event.artifact_update.artifact)
                parts.extend(extracted)
            elif isinstance(event, tuple) and len(event) == 2 and isinstance(event[1], TaskArtifactUpdateEvent):
                extracted = _extract_parts_from_artifact(event[1].artifact)
                parts.extend(extracted)

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
