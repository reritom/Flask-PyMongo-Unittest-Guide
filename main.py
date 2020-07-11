from src import create_app

if __name__=="__main__":
    db_uri = "mongodb://'127.0.0.1:27017/mydatabase"
    app = create_app(db_uri)
    app.run("0.0.0.0", port=5000, debug=False)
