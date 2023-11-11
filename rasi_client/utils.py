from pymongo import MongoClient
def get_db_handle(db_name, host, port, username, password):

 client = MongoClient(host=localhost,
                      port=int(27017),
                      username=username,
                      password=password
                     )
 db_handle = client['Queue']
 return db_handle, client