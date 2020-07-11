import unittest
from unittest.mock import patch
from mongomock import MongoClient
from src import create_app
import src.database

class PyMongoMock(MongoClient):
    def init_app(self, app):
        return super().__init__()

class TestArticles(unittest.TestCase):
    def test_create_article(self):
        request = {
            "author": "Mr Stark",
            "content": "This is a short dummy article",
            "tags": ["test"]
        }

        with patch.object(src.database, "mongo", PyMongoMock()):
            app = create_app("mongodb://localhost:27017/mydatabase").test_client()
            response = app.post("/articles", json=request)
            self.assertEqual(response.status_code, 201)

            # Validate the content
            response_json = response.get_json()
            expected_json = {
                "_id": response_json["_id"],
                "author": "Mr Stark",
                "content": "This is a short dummy article",
                "tags": ["test"]
            }
            self.assertEqual(response_json, expected_json)
