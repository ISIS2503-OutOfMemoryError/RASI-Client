"""
    Views
"""
from django.http import HttpResponse
from django.http import JsonResponse
from django.conf import settings
import requests


def conciliacion_bd(request):
    """
    @ppedreros
    Mientras se mantenga la conexión con la base de datos remota, se envían las peticiones almacenadas localmente. Se realiza hasta perder la conexión o hasta que la base de datos local quede vacía

    Args:
        request (_type_): _description_
    """
    settings.UNSYNC_LOCAL_BD = False


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


def get_test(request):
    """
    author: @c4ts0up
    Hace un GET de ejemplo. Si está conectado al LB, lo manda a a la app en nube. Si no, cae con gracia

    Args:
        request (_type_): _description_
    """
    url = settings.MANEJADOR_HC_URL + '/historia-clinica/1'
    print(settings.REMOTE_DB_ONLINE)
    
    # TODO: llamar al heartbeat o poner eso en un proceso paralelo?

    if not settings.REMOTE_DB_ONLINE:
        response_data = f'Error: {503}'
    elif settings.UNSYNC_LOCAL_DB:
        response_data = f'Error: cambios locales todavía no se han sincronizado'
    else:
        response = requests.get(url)

        if response.status_code == 200:
            response_data = response.text
        else:
            response_data = f'Error: {response.status_code}'


    return JsonResponse({'user_id': 1, 'external_data': response_data})


def post_test(request):
    """
    auhtor: @c4ts0up
    Hace un POST de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después

    Args:
        request (_type_): _description_
    """
    url = settings.MANEJADOR_HC_URL + '/historia-clinica/create/1'

    print(settings.REMOTE_DB_ONLINE)
    
    # TODO: llamar al heartbeat o poner eso en un proceso paralelo

    sample = {
        'name': 'James Bond',
        'tipo-sanguineo': 'A+',
        'fecha_nacimiento': '02-02-1990'
    }

    if not settings.REMOTE_DB_ONLINE:
        response_data = f'Error: {503}'
    elif settings.UNSYNC_LOCAL_DB:
        response_data = f'WARNING: no hay conexión a la aplicación. Los cambios se guardaran localmente'

        # TODO: guardar cambios localmente

    else:
        response = requests.get(url)

        if response.status_code == 200:
            response_data = response.text
        else:
            response_data = f'Error: {response.status_code}'


    return JsonResponse({'user_id': 1, 'external_data': response_data})


def put_test(request):
    """
    author: @ppedreros
    Hace un PUT de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después
    """
    pass

