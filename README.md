# Unit testing PyMongo Flask applications with MongoClient
## Introduction
This is a niche guide. The reason for this guide is that during a project, I needed to find a way to test a simple Flask PyMongo CRUD application. While attempting to test, I found little online documentation with regard to how to mock Mongo as part of my unit tests, and found no answers on StackOverflow that worked easily.

I found guides using PyTest, and guides that were for Flask apps that were using MongoClient and Connection. Neither of which satisfied the setup I was using. There were also testing solutions using mockupdb, but they seemed overly complex.

Seeing as many developers are introduced to web development through Flask, I thought this little guide might help someone some day. Note this guides skips a few practices to make the codebase smaller so we can focus on the matter at hand.

The specific stack I am using is:
- Flask
- PyMongo (using init_app)
- Unittest

## Application
The application we are intending to create is a simple CRUD application, made in Flask, with a MongoDB database. We will expose endpoints for creating, retrieving, and deleting "article" resources. The content of these resources is simply the "author", the "content", and a list of "tags".

All the code for this project can be found in the GitHub reposity: https://github.com/reritom/Flask-PyMongo-Unittest-Guide.

## Directory layout
We will follow a best practice regarding the setup of the repo. There will be a "src" directory for our source code, a "tests" directory for our tests, and the application would nominally be deployed by running "python main.py".

Our directory will look like this (ignoring the README, requirements.txt, and other miscellaneous files):
```
.
├── main.py
├── src
│   ├── __init__.py
│   ├── application.py
│   ├── database.py
│   └── controllers
│       ├── __init__.py
│       └── article_controller.py
└── tests
    ├── __init__.py
    └── articles_test.py
```

## src
If you have worked with Flask before, you will know there is typically an application.py (or sometimes you put this in the __init__.py of the src). Then, you create a database.py which will contain your database object. When you create your first Flask app, often you will put the database object in your application.py, but as soon as you start splitting your application, you encounter circular import problems if the database exists in your application.py. So we create two files: "database.py", "application.py".

The database.py is simple enough (though we will change this later). It starts by looking like this:
```
# src/database.py
from flask_pymongo import PyMongo

mongo = PyMongo()
```
Whenever we want to access our database, we import and interact with this single "PyMongo" instance, assigned to the variable "mongo".

The application will follow an application factory approach, and we will skip config objects because they don't matter in this case. So we can just pass the database address to it instead.

The application.py will look like this:
```
# src/application.py
from flask import Flask
from src.database import mongo
from src.controllers import ArticleController

def create_app(db_uri: str) -> Flask:
    app = Flask(__name__)
    app.config["MONGO_URI"] = db_uri
    mongo.init_app(app)

    # Add the articles collection if it doesn't already exist
    if not 'articles' in mongo.db.list_collection_names():
        articles_collection = mongo.db['articles']

    # Register the article routes
    app.add_url_rule("/articles", methods=["POST"], view_func=ArticleController.create_article)
    app.add_url_rule("/articles", methods=["GET"], view_func=ArticleController.get_articles)
    app.add_url_rule("/articles/<uuid:article_id>", methods=["GET"], view_func=ArticleController.get_article)
    app.add_url_rule("/articles/<uuid:article_id>", methods=["DELETE"], view_func=ArticleController.delete_article)

    return app
```

You notice we have a class called the ArticleController in the controller subdirectory. The reason we can import it directly from the controllers module, as opposed to importing it like "from src.controllers.article_controller import ArticleController", is because we have import the controller into the "src/controllers/__init__.py".

The ArticleController for now just focuses on the create_article aspect. For creating the article we won't do any validation. Instead we just take the content from the request, store it in our mongo collection, and return the data from the request along with the mongo document id, which resembles this:
```
# src/controllers/article_controller.py
import uuid
from flask import request, jsonify
from src.database import mongo

class ArticleController:
    @staticmethod
    def create_article():
        """
        Take the article from the request and deposit it directly into our mongo collection
        """
        data = request.get_json(force=True)
        mongo.db.articles.insert_one(data)
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
```

Finally, to run this application, we create the main.py, which can be just a few lines long in this case.
```
# main.py
from src import create_app

if __name__=="__main__":
    db_uri = "mongodb://'127.0.0.1:27017/mydatabase"
    app = create_app(db_uri)
    app.run("0.0.0.0", port=5000, debug=False)

```
Again, note that "create_app" can be imported directly from src, because in "src/__init__.py" I have added "from src.application import create_app". This is largely just for convenience when projects grow and become more nested.

Now, with just these four files, we are able to run our app and create articles by posting data to the "/articles" endpoint, assuming you are running mongodb in the background, and pass the correct db_uri to the create_app function.

## Testing
So we can have an application that we can run. Now we want to test it. There are plenty of reasons for testing, including the ensure the application fits the expected behaviour, and to make sure no regressions (bugs) get introduced into the code down the line.

When testing, we focus on the code, and our test should be decoupled from mongod so that the tests can be run easier, and so they aren't dependent on the mongod service.

The approach we take for this is called "mocking". We want to mock Mongo, which is akin to creating a fake mongo instance that appears to act in the same way as the real Mongo (though obviously the resemblance is usually skin-deep).

From the perspective of our code, we expect to be able to insert a document into our mocked mongo, and be able to retrieve in a later request.

To do this we will use a library called mongomock, which provides a class called MongoClient, which acts the same in most nominal cases as the PyMongo MongoClient.

### Patching
Patching is a way of replacing an object in the program namespace with something else. Often this is used to patch the environment or patch API calls. Imagine you have a script that runs in one way if os.environ["FLAG"] == True, and another way if os.environ["FLAG"] == False. You would want to create two tests, one for each case, and you then patch os.environ to set FLAG to the correct value for each test.

An important thing to note when patching, is that you patch and object in the namespace of the module which is consuming the object. What does this mean? Well, when you use os.environ, you import "os". Effectively it means in your module, there is now an object module called "os", and this is what you want to patch, because this is what your code is consuming when you use os.environ later.

Practically it is as follows:
```
# dummy.py
import os
def print_flag():
  print(os.environ.get("FLAG"))
```

```
# dummy_test.py
from unittest.mock import patch
from dummy import print_flag

# If we patch "os", we are patching it in the wrong namespace, so we can't control what will be printed.
with patch("os") as dummy_os:
  print_flag()

with patch("dummy.os") as dummy_os:
  dummy_os.environ.get.return_value = True
  print_flag() # This will print True, because we have patched the os in the namespace of dummy, and explicitly told the mock object (dummy_os) to return True when os.environ.get(...) is called.
```

In this case, when testing, we could patch every case where we import "mongo" from "app.database". In the namespace of each consumer, we could replace the mongo (MongoClient) object with our mongomock.MongoClient.

However, as your application grows, you would need to keep adding more patches, whenever the mongo client is consumed.

Seeing as all the database consumers import mongo from app.database, it would be convenient if we could patch "mongo" inside the app.database modules. Then all the consumers could continue to import this object while being none-the-wiser. In our tests, we would only need to make sure the database object is mocked, which means as our application grows, our tests will still be valid.

We could then consider that as our "src.database" imports PyMongo, we could mock PyMongo in the namespace of "src.database".

In your test you could try something like the following:
```
import unittest
from unittest.mock import patch
from src import create_app
import mongomock

class TestApplication(unittest.TestCase):
  def test_application(self):
    with patch("src.database.PyMongo", side_effect=mongomock.MongoClient):
      # Create the app and run the tests
      ...
```
Now the above code Would mock PyMongo to refer to mongomock.MongoClient, but your test would still fail. This is because the src.database module has already been loaded prior to running your test. So yes, PyMongo now refers to mongomock.MongoClient, but your mongo variable is assigned to an instance of PyMongo, because it was run prior to the mocking. So you are mocking the class, but too late.

You could then consider either trying to mock the src.database module before-hand, or patching the app.database.mongo object with our mongomock.MongoClient instance.

If we consider the latter, we can do it with some changes to our code. What we want, is to mock the "mongo" object in "src.database" so instead of referring to an instance of PyMongo, it now refers to an instance of mongomock.MongoClient. Now we need to remember namespaces. In both "src/application.py" and "src/controllers/article_controllers.py", we import "mongo". This means that in each of those namespaces, they already have an reference of mongo. So if we then patch "mongo" in the "src.database" module, it won't be reflected in the "mongo" object that exists in those two namespaces. So the code change we would need to make is to not import "mongo" into those two modules, and instead to import the "app.database" module, and access mongo by using "app.database.mongo".

These changes would like this this:
```
# src/application.py
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
    ...

    return app
```
and
```
# src/controllers/article_controller.py
from flask import request, jsonify
import src.database

class ArticleController:
    @staticmethod
    def create_article():
        data = request.get_json(force=True)
        src.database.mongo.db.articles.insert_one(data)
        data["_id"] = str(data["_id"]) # The mongo-added id isn't serialisable, so we convert it to a string
        return jsonify(data), 201
    ...
```

In our test, we can then patch the app.database module object so that mongo refers to our mongomock.MongoClient instance, instead of PyMongo.
```
# tests/articles_test.py
import unittest
from unittest.mock import patch
from src import create_app
import src.database
import mongomock

class TestApplication(unittest.TestCase):
  def test_application(self):
    with patch.object(src.database, "mongo", mongomock.MongoClient()):
      # Create the app and run the tests
      ...
```
At this point, we are patching the correct object in the correct namespace, and the consumers of mongo are getting our patched resource. However, flask_pymongo.PyMongo and mongomock.MongoClient aren't referencing the same type of object. PyMongo is a superclass of MongoClient. So you will get this error:
```
Traceback (most recent call last):
  File "/Users/***/projects/flask-pymongo-unittest-guide/tests/articles_test.py", line 20, in test_create_article
    app = create_app("mongodb://localhost:27017/mydatabase").test_client()
  File "/Users/***/projects/flask-pymongo-unittest-guide/src/application.py", line 8, in create_app
    src.database.mongo.init_app(app)
TypeError: 'Database' object is not callable
```
or if you patched with mongomock.MongoClient, and not mongomock.MongoClient(), you will get this error.
```
Traceback (most recent call last):
  File "/Users/***/projects/flask-pymongo-unittest-guide/tests/articles_test.py", line 20, in test_create_article
    app = create_app("mongodb://localhost:27017/mydatabase").test_client()
  File "/Users/***/projects/flask-pymongo-unittest-guide/src/application.py", line 8, in create_app
    src.database.mongo.init_app(app)
AttributeError: type object 'MongoClient' has no attribute 'init_app'
```
The latter error is a bug in your code, and once you fix it, you will get the first error instead.
To handle this, we will can create a dummy superclass that has the init_app method, and we can patch mongo with that instead:
```
# tests/articles_test.py
import unittest
from unittest.mock import patch
from src import create_app
import src.database
import mongomock

class PyMongoMock(MongoClient):
    def init_app(self, app):
        return super().__init__()

class TestApplication(unittest.TestCase):
  def test_application(self):
    with patch.object(src.database, "mongo", PyMongoMock()):
      # Create the app and run the tests
      ...
```
Note again that we are patching src.database.mongo with an instance of PyMongoMock, not the the class.

At this point your test will be able to be run successfully with a mocked instance of mongo. You can check out the specific tests I have written for this guide in the repo.

Patching is a very powerful tool in Python and the unittest framework, and writing strong, self-contained unit tests is how you guarantee your application behaves as expected. The combination of patching and namespaces can be confusing, and I have seen many tests where the environment has been patched incorrectly, leading to tests that are passing, but will likely fail on other machines, so its a very important part of the Python to learn about.

I hope this guide will help the one or two developers who encounter this testing hurdle.
