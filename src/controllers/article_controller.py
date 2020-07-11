import uuid
from flask import request, jsonify
import src.database

class ArticleController:
    @staticmethod
    def create_article():
        """
        Take the article from the request and deposit it directly into our mongo collection
        """
        data = request.get_json(force=True)
        src.database.mongo.db.articles.insert_one(data)
        data["_id"] = str(data["_id"]) # The mongo-added id isn't serialisable, so we convert it to a string
        return jsonify(data), 201

    @staticmethod
    def get_article(article_id: uuid.UUID):
        ...

    @staticmethod
    def get_articles():
        ...

    @staticmethod
    def delete_article(article_id: uuid.UUID):
        ...
