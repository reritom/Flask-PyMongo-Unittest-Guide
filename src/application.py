from flask import Flask
from src.controllers import ArticleController
import src.database

def create_app(db_uri: str) -> Flask:
    app = Flask(__name__)
    app.config["MONGO_URI"] = db_uri
    src.database.mongo.init_app(app)

    # Add the articles collection if it doesn't already exist
    if not 'articles' in src.database.mongo.db.list_collection_names():
        articles_collection = src.database.mongo.db['articles']

    # Register the article routes
    app.add_url_rule("/articles", methods=["POST"], view_func=ArticleController.create_article)
    app.add_url_rule("/articles", methods=["GET"], view_func=ArticleController.get_articles)
    app.add_url_rule("/articles/<uuid:article_id>", methods=["GET"], view_func=ArticleController.get_article)
    app.add_url_rule("/articles/<uuid:article_id>", methods=["DELETE"], view_func=ArticleController.delete_article)

    return app
