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

"""Firestore database client and collection helper functions.

Hardcodes project ID "qwiklabs-gcp-03-64eae057edee" directly for Firestore Client
to ensure compatibility when running on Agent Platform runtime.
"""

from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcode GCP Project ID string to prevent Agent Platform project number resolution issues
PROJECT_ID = "qwiklabs-gcp-03-64eae057edee"
COLLECTION_NAME = "user_health_profiles"


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_health_records(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves health and allergy records from Firestore collection.

    Args:
        user_id: Optional user identifier filter.

    Returns:
        List of health record dictionaries.
    """
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)
    
    if user_id:
        query = collection_ref.where("user_id", "==", user_id)
        docs = query.stream()
    else:
        docs = collection_ref.stream()

    records = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        records.append(data)
    return records


def add_health_record(
    allergy_name: str,
    severity: str,
    category: str,
    notes: str = "",
    user_id: str = "default_user",
) -> Dict[str, Any]:
    """Adds a new allergy/health record to Firestore.

    Args:
        allergy_name: Name of allergen/condition (e.g. Penicillin, Peanuts).
        severity: Severity level (e.g. Mild, Severe, Anaphylactic).
        category: Category (e.g. Food, Medication, Environmental).
        notes: Additional medical/dietary notes.
        user_id: User identifier string.

    Returns:
        Dictionary containing the saved record with its document ID.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document()
    
    record_data = {
        "user_id": user_id,
        "allergy_name": allergy_name,
        "severity": severity,
        "category": category,
        "notes": notes,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    
    doc_ref.set(record_data)
    record_data["id"] = doc_ref.id
    record_data["created_at"] = "just now"
    return record_data
