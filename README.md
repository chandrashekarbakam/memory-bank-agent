# 🧠 Memory Bank Agent

A stateful, AI-powered health and allergy tracking agent built with the **Google Agent Development Kit (ADK)**. The Memory Bank Agent retains user health conditions, allergies, and dietary preferences across sessions using **Vertex AI Memory Bank**, executes live database queries via **Cloud Firestore**, searches real-time FDA recall notices and USDA food nutrition data, locates nearby medical facilities with **Google Maps APIs**, generates visual meal representations and videos using **Vertex AI Imagen** and **Google Omni**, and renders adaptive user interface cards with **A2UI**.

![Memory Bank Agent Demo](./demo.gif)

---

## 🚀 Key Features & Implemented Capabilities

Based strictly on the codebase in `app/` and `agents-cli-manifest.yaml`, the Memory Bank Agent implements the following capabilities:

### 🧠 Cross-Session Memory (Vertex AI Memory Bank)
- **Preload Memory Tool (`PreloadMemoryTool`)**: Automatically fetches past user memories (allergies, medical history, dietary restrictions) at the start of a session.
- **Automated Memory Persistence (`generate_memories_callback`)**: Analyzes conversation turns and updates the Memory Bank asynchronously with newly stated health facts.

### 🗄️ Database & Health Record Management (Cloud Firestore)
- **`search_health_records`**: Queries stored user health logs, allergy entries, and medical notes from Cloud Firestore.
- **`create_health_record`**: Saves new user-reported allergies, sensitivities, or medical records directly into Firestore.

### 🥗 Real-Time Food Safety & Nutrition Data
- **`check_fda_recalls`**: Queries the openFDA REST API for active food enforcement recall notices by allergen or product keyword.
- **`search_usda_food_nutrition`**: Searches the USDA FoodData Central API for detailed ingredient breakdown and nutritional content.

### 📍 Location & Emergency Facility Finder (Google Maps APIs)
- **`geocode_address`**: Converts street addresses or location descriptions into latitude and longitude coordinates.
- **`find_nearby_places`**: Locates nearby hospitals, clinics, or pharmacies relative to user coordinates.

### 🎨 Visual & Multi-Modal Generation (Vertex AI Imagen & Google Omni)
- **`generate_item_image`**: Generates high-resolution food images using **Vertex AI Imagen 3** (`imagen-3.0-generate-002`), registers them with `tool_context.save_artifact`, and uploads them to a public Cloud Storage bucket.
- **`generate_item_video`**: Generates short video clips using Google's **Omni model** (`gemini-omni-flash-preview` in the `global` region), registers them as Playground Artifacts, and uploads them to public Cloud Storage.

### 🖥️ Adaptive User Interface (A2UI v0.8)
- **`a2ui_callback`**: Transforms model outputs into structured A2UI schema payloads (Cards, Columns, Rows, Text, Images) for clean client-side rendering.

### 💻 Code Execution Sandbox
- **`AgentEngineSandboxCodeExecutor`**: Executes Python code safely in the Agent Engine sandbox for complex health calculations and data processing.

---

## 🛠️ Google Cloud & External Integrations

| Integration / Service | Purpose | Implemented In |
| :--- | :--- | :--- |
| **Vertex AI Memory Bank** | Long-term cross-session memory storage | `app/agent.py` (`PreloadMemoryTool`, `generate_memories_callback`) |
| **Google Cloud Firestore** | NoSQL database for health records | `app/agent.py` (`search_health_records`, `create_health_record`) |
| **Google Cloud Storage** | Public asset hosting for generated images & videos | `app/agent.py` (`generate_item_image`, `generate_item_video`) |
| **Vertex AI Imagen 3** | Multi-modal image generation | `app/agent.py` (`imagen-3.0-generate-002`) |
| **Google Omni Model** | Multi-modal video generation | `app/agent.py` (`gemini-omni-flash-preview`) |
| **Google Maps Platform** | Geocoding and nearby place search | `app/agent.py` (`geocode_address`, `find_nearby_places`) |
| **openFDA API** | Live food recall enforcement data | `app/agent.py` (`check_fda_recalls`) |
| **USDA FoodData Central** | Ingredient & nutritional search | `app/agent.py` (`search_usda_food_nutrition`) |

---

## 🏗️ Project Architecture

```
.
├── app/
│   ├── agent.py            # Primary ADK agent definition, tools, and callbacks
│   ├── memory_utils.py     # Vertex AI Memory Bank API wrapper
│   └── a2ui_utils.py       # A2UI response formatter callback
├── frontend/
│   ├── main.py             # FastAPI proxy connecting UI to reasoning engine
│   └── static/
│       └── index.html      # Responsive Chat UI with A2UI card support
├── agents-cli-manifest.yaml# Manifest for Agent Platform deployment
├── demo.gif                # Looping demonstration GIF
└── pyproject.toml          # Python project dependencies
```

---

## 💻 Local Setup & Running Instructions

### Prerequisites
- Python 3.10+
- Google Cloud SDK (`gcloud`) authenticated to your GCP project
- `uv` package manager installed (`pip install uv`)

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure Environment Variables
Set your environment variables before running the application:
```bash
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
export AGENT_ENGINE_RESOURCE_NAME="projects/<project-number>/locations/<region>/reasoningEngines/<engine-id>"
export AGENT_DIRECTORY="app"
```

### 3. Run the Frontend Proxy Locally
Navigate to the `frontend/` directory and launch the server:
```bash
cd frontend
uv run python main.py
```
The server will start on port `8080`.

### 4. Deploying to Cloud Run (Optional)
To deploy the frontend proxy to Google Cloud Run:
```bash
gcloud run deploy memory-bank-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=$AGENT_ENGINE_RESOURCE_NAME,AGENT_DIRECTORY=$AGENT_DIRECTORY"
```
