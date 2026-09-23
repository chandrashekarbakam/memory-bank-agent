#!/usr/bin/env python3
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

"""Seed script for populating initial Firestore health & allergy records."""

import sys
from google.cloud import firestore

# Hardcode project ID to avoid Agent Platform project number resolution issues
PROJECT_ID = "qwiklabs-gcp-03-64eae057edee"
COLLECTION_NAME = "user_health_profiles"

SEEDED_ITEMS = [
    {
        "user_id": "default_user",
        "allergy_name": "Penicillin",
        "severity": "Anaphylactic",
        "category": "Medication",
        "notes": "Causes severe rash and breathing difficulty. Strict avoidance required.",
    },
    {
        "user_id": "default_user",
        "allergy_name": "Peanuts",
        "severity": "Severe",
        "category": "Food",
        "notes": "Triggers severe allergic reaction. Carry EpiPen at all times.",
    },
    {
        "user_id": "default_user",
        "allergy_name": "Dust Mites",
        "severity": "Mild",
        "category": "Environmental",
        "notes": "Causes sneezing and nasal congestion during spring/autumn.",
    },
    {
        "user_id": "user_alice",
        "allergy_name": "Gluten",
        "severity": "Moderate",
        "category": "Food",
        "notes": "Celiac sensitivity. Requires strict gluten-free meal planning.",
    },
]


def seed_firestore():
    print(f"Connecting to Firestore for project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(COLLECTION_NAME)

    for item in SEEDED_ITEMS:
        item["created_at"] = firestore.SERVER_TIMESTAMP
        doc_ref = collection_ref.document()
        doc_ref.set(item)
        print(f"  + Seeded record '{item['allergy_name']}' ({item['category']}) with doc ID: {doc_ref.id}")

    print("✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed_firestore()
