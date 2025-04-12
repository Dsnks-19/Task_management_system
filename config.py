import os
import json
from google.cloud import firestore

# Set the environment variable to point to your service account key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"

# Initialize Firestore client
db = firestore.Client()

# Firebase Web configuration (you'll get this from Firebase console)
firebase_config = {
    "apiKey": "AIzaSyCtqDIwwyY15wL3zdlHdJn66goUoVdzrwQ",
    "authDomain": "task-management-4eb9a.firebaseapp.com",
    "projectId": "task-management-4eb9a",
    "storageBucket": "task-management-4eb9a.firebasestorage.app",
    "messagingSenderId": "803979943759",
    "appId": "1:803979943759:web:4610da98017218c50def3a"
}