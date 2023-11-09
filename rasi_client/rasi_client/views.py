"""
    Views
"""
from django.http import HttpResponse


remote_bd_online = False


def health_check(request):
    """
    @c4ts0up
    Revisa que el balanceador de cargas módulos IPS este arriba
    UP -> UP        :   no cambia
    UP -> DOWN      :   cambia a BD local
    DOWN -> UP      :   concilia y cambia a BD en cloud cuando complete conciliación
    DOWN -> DOWN    :   no cambia

    Args:
        request (_type_): _description_
    """
    pass


def conciliacion_bd(request):
    """
    @ppedreros
    Mientras se mantenga la conexión con la base de datos remota, se envían las peticiones almacenadas localmente. Se realiza hasta perder la conexión o hasta que la base de datos local quede vacía

    Args:
        request (_type_): _description_
    """
    pass



def get_test(request):
    """
    @c4ts0up
    Hace un GET de ejemplo. Si está conectado al LB, lo manda a a la app en nube. Si no, cae con gracia

    Args:
        request (_type_): _description_
    """
    pass


def post_test(request):
    """
    @c4ts0up
    Hace un POST de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después

    Args:
        request (_type_): _description_
    """
    pass


def put_test(request):
    """
    @ppedreros
    Hace un PUT de ejemplo. Si está conectado al LB, lo manda a la app en nube. Si no, guarda la petición en la base de datos local para realizarla después
    """
    pass

