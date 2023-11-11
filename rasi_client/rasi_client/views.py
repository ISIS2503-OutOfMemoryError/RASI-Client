"""
    Views
"""
from django.http import HttpResponse
from django.http import JsonResponse
from django.conf import settings
import requests
import pymongo
from django.views.decorators.csrf import csrf_exempt
import json


queue_client = pymongo.MongoClient("mongodb://localhost:27017/")
dbname = queue_client['local_queue']
collection = dbname['queries']

@csrf_exempt
def conciliacion_bd(request):
    """
    @author: ppedreros
    Mientras se mantenga la conexión con la base de datos remota, se envían las peticiones almacenadas localmente. Se realiza hasta perder la conexión o hasta que la base de datos local quede vacía

    Args:
        request (_type_): _description_
    """
    # cuenta los documentos
    count = collection.count_documents({})

    # mientras haya documentos por enviar
    while count != 0:
        query = collection.find_one()
        payload = query.get('data')

        print(query)

        # TODO! Cuidado con ciclo infinito: podría estar mandando localmente
        if query.get('method') == 'POST':
            response = post_test(payload, conciliacion=True)
        elif query.get('method') == 'PUT':
            response = put_test(payload, conciliacion=True)

        data = json.loads(response.content.decode('utf-8'))
        print("data", data)

        # evaluamos la respuesta
        # se perdió la conexión en conciliación
        if data.get('sent_to_cloud') is False :
            break

        # se mantiene la conexión en conciliación
        collection.delete_one({"_id":query['_id']})
        count = collection.count_documents({})


    settings.UNSYNC_LOCAL_DB = (bool)(collection.count_documents({}) > 0)
    
    return JsonResponse({'user_id': 1, 'local_unsync_transactions': collection.count_documents({})})


def is_online(request):
    """
    @author: c4ts0up
    Consulta si el LB está vivo. 200 si sí, 503 si no

    Args:
        request (_type_): _description_
    """
    
    url = settings.MANEJADOR_HC_URL + '/heartbeat'
    print("Pinging", url)
    # estableció la conexión y obtuvo respuesta
    try:
        response = requests.get(url)
        
        if (response.status_code == 200):
            return True
        else:
            return False
        
    # no pudo establecer la conexión
    except:
        return False


@csrf_exempt
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
            # hay cambios para sincronizar
            if settings.UNSYNC_LOCAL_DB:
                conciliacion_bd(request)
            return HttpResponse(200)
        
        # -> DOWN
        settings.REMOTE_DB_ONLINE = False
        settings.UNSYNC_LOCAL_DB = True
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
def get_test(request, conciliacion=False):
    """
    author: @c4ts0up
    Hace un GET de ejemplo. Si está conectado al LB, lo manda a a la app en nube. Si no, cae con gracia

    Args:
        request (_type_): _description_
    """
    url = settings.MANEJADOR_HC_URL + '/historia-clinica/get/34'

    try:
        # cambios locales no sincronizados
        if settings.UNSYNC_LOCAL_DB and not conciliacion:
            response_data = "Error: cambios locales no se han sincronizado"
            return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=500)

        # intenta hacer GET a la app en nube
        response = requests.get(url)

        # GET exitoso
        if response.status_code == 200:
            response_data = response.text
            return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': True}, status=200)

        # GET fallido
        response_data = "Error: manejador de historias clínicas es inaccesible"
        # no hay manera de arreglarlo
        return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=503)
    
    # fallo en la conexión = GET fallido
    except:
        response_data = "Error: manejador de historias clínicas es inaccesible"

        
        # no hay manera de arreglarlo
        return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=503)


@csrf_exempt
def post_test(request, conciliacion=False):
    """
    author: @c4ts0up
    Hace un POST de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después

    Args:
        request (_type_): _description_
    """
    url = settings.MANEJADOR_HC_URL + '/historia-clinica/create/'

    # Datos de prueba
    sample_data = {
        'id' : 1000,
        'nombre' : 'James Bond',
        'tipo_sanguineo' : 'A+',
        'genero' : 'M',
    }

    json_data = json.dumps(sample_data)


    try:
        # cambios locales no sincronizados
        if settings.UNSYNC_LOCAL_DB and not conciliacion:
            response_data = "Warning: cambios locales no se han sincronizado. Transacción será almacenada localmente."

            # guarda transacción localmente
            collection.insert_one({
                'data': json_data,
                'method': "POST"
            })

            return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=200)

        # intenta hacer POST a la app en nube
        # TODO: Cambiar por request para probar fuera de pruebas
        response = requests.post(url, data=json_data)

        print("Llega acá")
        # POST exitoso
        if response.status_code in [200, 204]:
            response_data = response.text
            return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': True}, status=200)

        # POST fallido
        response_data = "Warning: manejador de historias clínicas es inaccesible. Transacción será almacenada localmente."

        # guarda transacción localmente
        if not conciliacion:
            collection.insert_one({
                'data': json_data,
                'method': "POST"
            })

        settings.UNSYNC_LOCAL_DB = True

        return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=200)
    
    # fallo en la conexión = POST fallido
    except:
        response_data = "Warning: cambios locales no se han sincronizado. Transacción será almacenada localmente."

        # guarda transacción localmente
        if not conciliacion:
                collection.insert_one({
                'data': json_data,
                'method': "POST"
            })
                
        settings.UNSYNC_LOCAL_DB = True

        return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=200)


@csrf_exempt
def put_test(request, conciliacion=False):
    """
    author: @ppedreros
    Hace un PUT de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después
    """
    url = settings.MANEJADOR_HC_URL + '/historia-clinica/1'

    # Datos de prueba
    sample_data = {
        'id' : 1000,
        'nombre' : 'James H Bond',
        'tipo_sanguineo' : 'AB+',
        'genero' : 'H',
    }

    json_data = json.dumps(sample_data)

    try:
        # cambios locales no sincronizados
        if settings.UNSYNC_LOCAL_DB and not conciliacion:
            response_data = "Warning: cambios locales no se han sincronizado. Transacción será almacenada localmente."

            # guarda transacción localmente
            collection.insert_one({
                'data': json_data,
                'method': "PUT"
            })

            return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=200)

        # intenta hacer PUT a la app en nube
        response = requests.put(url, data=request.body)

        # PUT exitoso
        if response.status_code == 200:
            response_data = response.text
            return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': True}, status=200)

        # PUT fallido
        response_data = "Warning: manejador de historias clínicas es inaccesible. Transacción será almacenada localmente."

        # guarda transacción localmente
        if not conciliacion:
                collection.insert_one({
                'data': json_data,
                'method': "PUT"
            })

        settings.UNSYNC_LOCAL_DB = True

        return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=200)
    

    # fallo en la conexión = POST fallido
    except:
        response_data = "Warning: cambios locales no se han sincronizado. Transacción será almacenada localmente."

        # guarda transacción localmente
        if not conciliacion:
            collection.insert_one({
                'data': json_data,
                'method': "PUT"
            })

        settings.UNSYNC_LOCAL_DB = True

        return JsonResponse({'user_id': 1, 'external_data': response_data, 'sent_to_cloud': False}, status=200)


