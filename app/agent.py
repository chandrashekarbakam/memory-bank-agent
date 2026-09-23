# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


MODEL = "gemini-3.8-flash"


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from app.firestore_service import add_health_record, list_health_records


def search_health_records(user_id: str = "default_user") -> str:
    """Searches and lists health, allergy, and medical profile records stored in Firestore.

    Args:
        user_id: The user ID to retrieve health records for (defaults to 'default_user').

    Returns:
        A string formatted list of stored health and allergy records.
    """
    records = list_health_records(user_id=user_id)
    if not records:
        return f"No health records found in Firestore for user '{user_id}'."
    
    result = [f"Found {len(records)} health record(s) for user '{user_id}':"]
    for r in records:
        result.append(
            f"- [{r.get('category', 'General')}] {r.get('allergy_name')} (Severity: {r.get('severity')}): {r.get('notes')}"
        )
    return "\n".join(result)


def create_health_record(
    allergy_name: str,
    severity: str,
    category: str,
    notes: str = "",
    user_id: str = "default_user",
) -> str:
    """Creates and persists a new allergy or health record in Firestore database.

    Args:
        allergy_name: Name of allergen or medical condition (e.g., 'Penicillin', 'Peanuts', 'Gluten').
        severity: Severity level (e.g., 'Mild', 'Moderate', 'Severe', 'Anaphylactic').
        category: Category of allergen (e.g., 'Food', 'Medication', 'Environmental').
        notes: Additional notes or symptoms to record.
        user_id: User identifier to attach record to.

    Returns:
        Confirmation message with doc ID.
    """
    res = add_health_record(
        allergy_name=allergy_name,
        severity=severity,
        category=category,
        notes=notes,
        user_id=user_id,
    )
    return f"Successfully saved health record for '{allergy_name}' (ID: {res['id']}) in Firestore."


import json
import urllib.parse
import urllib.request


def check_fda_recalls(allergen_or_food: str) -> str:
    """Queries the OpenFDA Food Enforcement API for active food recalls matching an allergen or food item.

    Args:
        allergen_or_food: The allergen or food name to search for (e.g. 'peanut', 'milk', 'egg', 'sesame').

    Returns:
        A string summary of recent FDA enforcement recall notices.
    """
    query = urllib.parse.quote(allergen_or_food)
    url = f"https://api.fda.gov/food/enforcement.json?search=reason_for_recall:\"{query}\"&limit=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ADK-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = data.get("results", [])
            if not results:
                return f"No active FDA food recalls found for '{allergen_or_food}'."

            lines = [f"Found {len(results)} recent FDA recall notice(s) related to '{allergen_or_food}':"]
            for r in results:
                product = r.get("product_description", "Unknown product")[:120]
                reason = r.get("reason_for_recall", "Unspecified reason")[:120]
                status = r.get("status", "Ongoing")
                lines.append(f"- [{status}] Product: {product}... | Reason: {reason}...")
            return "\n".join(lines)
    except Exception as e:
        return f"Unable to fetch FDA recalls for '{allergen_or_food}': {str(e)}"


import os


def search_usda_food_nutrition(query: str) -> str:
    """Queries the USDA FoodData Central API for food items, ingredients, and nutrition details.

    Args:
        query: The food product or ingredient name to search for (e.g. 'peanut butter', 'almond milk').

    Returns:
        A formatted summary of matching food items and their ingredients.
    """
    api_key = os.getenv("FDC_API_KEY", "DEMO_KEY")
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={encoded_query}&pageSize=3&api_key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ADK-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            foods = data.get("foods", [])
            if not foods:
                return f"No USDA food entries found for '{query}'."

            lines = [f"Found {len(foods)} USDA food record(s) for '{query}':"]
            for f in foods:
                desc = f.get("description", "Unknown food")
                brand = f.get("brandOwner", "Generic")
                ingr = f.get("ingredients", "No detailed ingredients list available.")
                lines.append(f"- Product: {desc} (Brand: {brand}) | Ingredients: {ingr[:150]}")
            return "\n".join(lines)
    except Exception as e:
        return f"Unable to fetch USDA food data for '{query}': {str(e)}"


def geocode_address(address: str) -> str:
    """Converts a street address or city name into geographic coordinates (latitude & longitude) using Google Geocoding API.

    Args:
        address: The location, city, or street address to geocode (e.g. 'San Francisco, CA').

    Returns:
        A string formatted result containing the formatted address, latitude, and longitude.
    """
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not maps_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={maps_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ADK-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = data.get("results", [])
            if not results:
                return f"No geocoding results found for address: '{address}'."

            first = results[0]
            fmt_addr = first.get("formatted_address", address)
            location = first.get("geometry", {}).get("location", {})
            lat = location.get("lat")
            lng = location.get("lng")
            return f"Address: '{fmt_addr}' | Location Coordinates: (lat: {lat}, lng: {lng})"
    except Exception as e:
        return f"Unable to geocode address '{address}': {str(e)}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "hospital",
    radius_meters: float = 5000.0,
) -> str:
    """Finds nearby places of a specific type around a latitude/longitude coordinate using Google Places API (New).

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g. 'hospital', 'pharmacy', 'doctor', 'restaurant').
        radius_meters: Search radius in meters (defaults to 5000.0).

    Returns:
        A string list of nearby places with name, formatted address, and location coordinates.
    """
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not maps_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not configured."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": maps_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    try:
        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            places = data.get("places", [])
            if not places:
                return f"No nearby places of type '{place_type}' found within {radius_meters}m of ({latitude}, {longitude})."

            lines = [f"Found {len(places)} nearby '{place_type}' location(s):"]
            for p in places:
                name = p.get("displayName", {}).get("text", "Unknown Name")
                addr = p.get("formattedAddress", "No address")
                loc = p.get("location", {})
                plat = loc.get("latitude")
                plng = loc.get("longitude")
                lines.append(f"- Name: {name} | Address: {addr} | Location: (lat: {plat}, lng: {plng})")
            return "\n".join(lines)
    except Exception as e:
        return f"Unable to find nearby places for ({latitude}, {longitude}): {str(e)}"


import uuid
from google import genai
from google.cloud import storage
from google.adk.tools import ToolContext


async def generate_item_image(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates an image for a food item or allergen-free dish using gemini-3.1-flash-lite-image model in global region.

    Saves the generated image as a Playground Artifact and uploads it to public Cloud Storage.

    Args:
        prompt: Description of the food or health item image to generate (e.g. 'Gluten-free allergen-safe berry parfait').
        tool_context: ToolContext provided automatically by the framework.

    Returns:
        The public HTTPS Cloud Storage URL of the generated image.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project="qwiklabs-gcp-03-64eae057edee",
            location="global",
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"High quality professional photo of: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        img_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    img_bytes = part.inline_data.data
                    break

        if not img_bytes:
            return f"Failed to generate image bytes for prompt '{prompt}'."

        # (1) Save artifact with tool_context.save_artifact
        filename = f"food_image_{uuid.uuid4().hex[:8]}.jpg"
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # (2) Upload image bytes to public GCS bucket
        bucket_name = "memory-bank-agent-assets-qwiklabs-03"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"images/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(img_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        return f"Successfully generated image for '{prompt}'!\nPlayground Artifact: {filename}\nPublic Image URL: {public_url}"
    except Exception as e:
        return f"Error generating item image for '{prompt}': {str(e)}"


async def generate_item_video(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates a short video for a food item, allergen-free dish, or health demonstration using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the generated video as a Playground Artifact and uploads it to public Cloud Storage.

    Args:
        prompt: Description of the food or health video to generate (e.g. 'Gluten-free allergen-safe berry parfait preparation').
        tool_context: ToolContext provided automatically by the framework.

    Returns:
        The public HTTPS Cloud Storage URL of the generated video.
    """
    try:
        genai_client = genai.Client(
            vertexai=True,
            project="qwiklabs-gcp-03-64eae057edee",
            location="global",
        )
        res = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Generate a short video clip showing: {prompt}",
            response_modalities=["text", "video"],
        )

        video_bytes = None
        if hasattr(res, "output_video") and res.output_video and hasattr(res.output_video, "data"):
            data_val = res.output_video.data
            if isinstance(data_val, bytes):
                video_bytes = data_val
            elif isinstance(data_val, str):
                import base64
                video_bytes = base64.b64decode(data_val)

        if not video_bytes and hasattr(res, "steps") and res.steps:
            for s in res.steps:
                if hasattr(s, "content") and s.content:
                    for part in s.content:
                        if hasattr(part, "inline_data") and part.inline_data:
                            if getattr(part.inline_data, "mime_type", "").startswith("video/"):
                                video_bytes = part.inline_data.data
                                break

        if not video_bytes:
            return f"Failed to generate video bytes for prompt '{prompt}'."

        filename = f"food_video_{uuid.uuid4().hex[:8]}.mp4"
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        bucket_name = "memory-bank-agent-assets-qwiklabs-03"
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"videos/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        return f"Successfully generated video for '{prompt}'!\nPlayground Artifact: {filename}\nPublic Video URL: {public_url}"
    except Exception as e:
        return f"Error generating item video for '{prompt}': {str(e)}"


from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

from google.adk.code_executors import AgentEngineSandboxCodeExecutor

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name="projects/449481897749/locations/us-east1/reasoningEngines/2470129837612728320"
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a helpful AI assistant with cross-session memory capabilities. "
        "Pay special attention to and remember all user allergies, health conditions, "
        "dietary restrictions, and personal preferences stated across conversations. "
        "Always check preloaded memories, search/create health records in Firestore, "
        "check_fda_recalls for active recall notices, search_usda_food_nutrition for food data, "
        "use geocode_address / find_nearby_places to locate medical facilities or hospitals near the user, "
        "use generate_item_image / generate_item_video to create visual representations or videos of safe food items, "
        "and use Python code execution in your sandbox environment whenever complex calculations or data analysis are needed."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    # Keep in sync with agents-cli-manifest.yaml: agents-cli derives this name
    # from the project `name:` recorded there, and telemetry reports it as
    # gen_ai.agent.name. Renaming the agent only here makes the two disagree,
    # and anything selecting traces by name stops finding this agent's.
    name="simple_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        search_health_records,
        create_health_record,
        check_fda_recalls,
        search_usda_food_nutrition,
        geocode_address,
        find_nearby_places,
        generate_item_image,
        generate_item_video,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)


