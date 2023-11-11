"""
    Views
"""
from django.http import HttpResponse
from django.conf import settings
import requests
import pymongo
from django.views.decorators.csrf import csrf_exempt
import json


queue_client = pymongo.MongoClient("mongodb://localhost:27017/")
dbname = queue_client['local_queue']
collection = dbname['queries']

def home(request):
    return HttpResponse("Hello, Django!")

@csrf_exempt
def conciliacion_bd(request):
    """
    @ppedreros
    Mientras se mantenga la conexión con la base de datos remota, se envían las peticiones almacenadas localmente. Se realiza hasta perder la conexión o hasta que la base de datos local quede vacía

    Args:
        request (_type_): _description_
    """
    count = collection.count_documents({})
    print(count)
    while count != 0:
        query = collection.find_one()
        #post_test(query)
        collection.delete_one({"_id":query['_id']})
        count = collection.count_documents({})
    print(count)
    
    return HttpResponse("OK")


def is_online(request):
    """
    @author: c4ts0up
    Consulta si el LB está vivo. 200 si sí, 503 si no

    Args:
        request (_type_): _description_
    """
    LB_URL = 'google.com'
    LB_PORT = '80'
    LB_RESOURCE = ''
    url = 'http://' + LB_URL + ':' + LB_PORT + '/' + LB_RESOURCE
    print("Pinging", url)

    response = requests.get(url)
    
    if (response.status_code == 200):
        return True
    else:
        return False


def heartbeat(request):
    """
    auhtor: @c4ts0up
    Revisa que el balanceador de cargas módulos IPS este arriba
    UP -> UP        :   no cambia
    UP -> DOWN      :   cambia a BD local
    DOWN -> UP      :   concilia y cambia a BD en cloud cuando complete conciliación
    DOWN -> DOWN    :   no cambia

    Args:
        request (_type_): _description_
    """

    # analiza la respuesta
    alive = is_online(request)

    # UP ->
    if settings.REMOTE_DB_ONLINE:
        # -> UP
        if alive:
            return HttpResponse(200)
        
        # -> DOWN
        settings.REMOTE_DB_ONLINE = False
        return HttpResponse(503)

    # DOWN ->
    else:
        # -> DOWN
        if not alive:
            return HttpResponse(503)

        # UP
        settings.REMOTE_DB_ONLINE = True
        conciliacion_bd(request)
        return HttpResponse(200)

@csrf_exempt
def get_test(request):
    """
    author: @c4ts0up
    Hace un GET de ejemplo. Si está conectado al LB, lo manda a a la app en nube. Si no, cae con gracia

    Args:
        request (_type_): _description_
    """
    pass

@csrf_exempt
def post_test(request):
    """
    auhtor: @c4ts0up
    Hace un POST de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después

    Args:
        request (_type_): _description_
    """
    query = collection.insert_one({"path":request.path,"body":request.body,"method":request.method}).inserted_id

    return HttpResponse("OK")

@csrf_exempt
def put_test(request):
    """
    author: @ppedreros
    Hace un PUT de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después
    """
    pass

