from collections import defaultdict
import shelve
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import F, Q
from whoosh.index import open_dir
from whoosh.qparser import AndGroup, OrGroup, MultifieldParser
from main.populateDB import populate, INDEX_NAME
from main.sistema_recomendacion import *
from main.models import *
from main.forms import *


def index(request):
    return render(request, 'index.html', {'STATIC_URL':settings.STATIC_URL})


def ingresar(request):
    formulario = LoginForm()
    error = None
    next_url = request.GET.get('next')

    if request.method=='POST':
        formulario = LoginForm(request.POST)
        
        usuario=request.POST['username']
        clave=request.POST['password']
        acceso=authenticate(username=usuario,password=clave)
        if acceso is not None:
            if acceso.is_active:
                login(request, acceso)
                return HttpResponseRedirect(next_url or '/')
            else:
                error = "Usuario no activo"
        else:
            error = "Usuario o contraseña incorrectos"
                     
    return render(request, 'ingresar.html', 
                  {'formulario':formulario, 'error':error, 'next_url':next_url, 'STATIC_URL':settings.STATIC_URL})

def cerrar_sesion(request):
    logout(request)
    return HttpResponseRedirect('/')


### ADMIN

@login_required(login_url='/ingresar')
def cargar_bd(request):
    metadata = Metadata.objects.first()
    texto = "¿Seguro que quieres borrar y recargar la base de datos?"

    if request.method == "POST":
        (d,e,j) = populate()
        info={'Juegos':j, 'Desarrolladores':d, 'Etiquetas':e}
        return render(request, 'carga.html', {'info':info, 'STATIC_URL':settings.STATIC_URL})

    return render(request, 'confirmar_carga.html', {'texto': texto, 'ultima_carga': metadata.ultima_carga if metadata else None, 'STATIC_URL':settings.STATIC_URL})


@login_required(login_url='/ingresar')
def cargar_rs(request):
    texto = "¿Seguro que quieres recargar el sistema de recomendación?"
    
    if request.method == "POST":
        guardar_scores_juegos()
        messages.success(request, "Sistema de recomendación cargado correctamente.")
        return HttpResponseRedirect("/")

    return render(request, 'confirmar_carga.html', {'texto': texto, 'STATIC_URL':settings.STATIC_URL})





### LISTS

# Lists the games marked as liked by the current user
@login_required(login_url='/ingresar')
def juegos_gustados(request):
    if request.method == "POST" and "limpiar_favoritos" in request.POST:
        request.user.juegos_gustados.clear()
        return HttpResponseRedirect('/juegos_gustados')

    juegos = request.user.juegos_gustados.all().order_by('titulo')
    añadir_descripciones_whoosh(juegos)

    return render(request, 'juegos_gustados.html', {'juegos': juegos,'STATIC_URL': settings.STATIC_URL})


# Lists the 10 most popular games historically (by peak player count)
def top_10_juegos_populares(request):
    juegos = Juego.objects.all().order_by('-peak_jugadores')[:10]
    añadir_descripciones_whoosh(juegos)
    return render(request, 'top_10_juegos_populares.html', {'juegos': juegos, 'STATIC_URL':settings.STATIC_URL})


# Lists developers with free games, and for each one lists those games ordered by date
# The render will initially show only those with more than one game, but allowing the user to expand the list
def juegos_gratis_por_desarrollador(request):
    juegos = Juego.objects.filter(precio=0)
    añadir_descripciones_whoosh(juegos)

    devs_juegos = defaultdict(list)
    for juego in juegos:
        for dev in juego.desarrolladores.all():
            devs_juegos[dev].append(juego)

    devs_juegos = dict(sorted(devs_juegos.items(), key=lambda item: len(item[1]), reverse=True))
    for dev in devs_juegos:
        devs_juegos[dev].sort(key=lambda j: j.fecha)
        
    return render(request, 'juegos_gratis_por_desarrollador.html', {'devs_juegos': devs_juegos, 'STATIC_URL':settings.STATIC_URL})


### SEARCH

# Game search with filters (date range, maximum price, and tag) and sorting options (date, price, or popularity)
def filtrar_juegos(request):
    formulario = BusquedaJuegosFiltros()
    juegos = None

    form_fav = JuegosFavoritos(
        initial={"juegos": Juego.objects.all().filter(usuarios_gustan=request.user) if request.user.is_authenticated else []}
    )

    if request.method == "POST":
        # Preserve previous filters when saving favorites
        if 'guardar_favoritos' in request.POST:
            form_fav = JuegosFavoritos(request.POST)
            formulario = BusquedaJuegosFiltros(request.session.get('filtros_juegos') or None)
        else:
            formulario = BusquedaJuegosFiltros(request.POST)

        if formulario.is_valid():
            juegos = Juego.objects.all()

            fecha_inicio = formulario.cleaned_data['fecha_inicio']
            fecha_fin = formulario.cleaned_data['fecha_fin']
            precio_max = formulario.cleaned_data['precio_max']
            etiqueta = formulario.cleaned_data['etiqueta']
            ordenar_por = formulario.cleaned_data['ordenar_por']

            # Filters
            if fecha_inicio:
                juegos = juegos.filter(Q(fecha__gte=fecha_inicio) | Q(fecha__isnull=True))  # Juegos futuros se consideran posteriores a la fecha
            if fecha_fin:
                juegos = juegos.filter(fecha__lte=fecha_fin)
            if precio_max is not None:
                juegos = juegos.filter(precio__lte=precio_max)
            if etiqueta:
                juegos = juegos.filter(etiquetas=etiqueta)

            # Sorting
            if ordenar_por == 'titulo':
                juegos = juegos.order_by('titulo')
            elif ordenar_por == 'fecha':
                juegos = juegos.order_by(F('fecha').desc(nulls_first=True)) # Games scheduled in the future are considered more recent
            elif ordenar_por == 'precio':
                juegos = juegos.order_by(F('precio').asc(nulls_last=True))  # Games without a price are shown at the end
            elif ordenar_por == 'peak_jugadores':
                juegos = juegos.order_by('-peak_jugadores')

            if 'guardar_favoritos' not in request.POST:
                request.session['filtros_juegos'] = request.POST.dict()

        if form_fav.is_valid() and 'guardar_favoritos' in request.POST:
            juegos_selecc = form_fav.cleaned_data['juegos']
            juegos_visibles = juegos or Juego.objects.none()

            request.user.juegos_gustados.add(*juegos_selecc)    # Add selected visible games to user favorites
            request.user.juegos_gustados.remove(*juegos_visibles.exclude(pk__in=juegos_selecc))   # Remove visible games that were not selected

            messages.success(request, "Favoritos actualizados correctamente")

    añadir_descripciones_whoosh(juegos)

    return render(request, 'filtrar_juegos.html', {'formulario': formulario, 'juegos': juegos, 'form_fav': form_fav, 'STATIC_URL':settings.STATIC_URL})


# Game search by keywords, specifying where to search (title, description, about, and/or reviews) and the search type (OR or AND)
def buscar_juegos_texto(request):
    formulario = BusquedaJuegosTexto()
    juegos = None

    form_fav = JuegosFavoritos(
        initial={"juegos": Juego.objects.all().filter(usuarios_gustan=request.user) if request.user.is_authenticated else []}
    )

    if request.method == "POST":
        # Preserve previous filters when saving favorites
        if 'guardar_favoritos' in request.POST:
            form_fav = JuegosFavoritos(request.POST)
            formulario = BusquedaJuegosTexto(request.session.get('filtros_juegos') or None)
        else:
            formulario = BusquedaJuegosTexto(request.POST)

        if formulario.is_valid():
            texto = formulario.cleaned_data["texto"]

            # Where to search
            campos = [c for c in ["titulo", "descripcion", "about", "reviews"] if formulario.cleaned_data[c]]

            # How to search
            tipo_busqueda = formulario.cleaned_data["tipo_busqueda"]
            group = AndGroup if tipo_busqueda == "AND" else OrGroup

            ids_resultado = []
            ix = open_dir(INDEX_NAME)
            with ix.searcher() as searcher:
                parser = MultifieldParser(campos, ix.schema, group=group)
                query = parser.parse(texto)
                results = searcher.search(query, limit=10)

                for r in results:
                    ids_resultado.append(int(r["juego_id"]))

            juegos_qs = Juego.objects.filter(juego_id__in=ids_resultado)
            juegos = sorted(juegos_qs, key=lambda j: ids_resultado.index(j.juego_id))

            if 'guardar_favoritos' not in request.POST:
                request.session['filtros_juegos'] = request.POST.dict()

        if form_fav.is_valid() and 'guardar_favoritos' in request.POST:
            juegos_selecc = form_fav.cleaned_data['juegos']
            juegos_visibles = juegos_qs or Juego.objects.none()

            request.user.juegos_gustados.add(*juegos_selecc)    # Add selected visible games to user favorites
            request.user.juegos_gustados.remove(*juegos_visibles.exclude(pk__in=juegos_selecc))   # Remove visible games that were not selected

            messages.success(request, "Favoritos actualizados correctamente")

    añadir_descripciones_whoosh(juegos)

    return render(request, "buscar_juegos_texto.html", {"formulario": formulario, 'juegos': juegos, 'STATIC_URL':settings.STATIC_URL})


### RECOMMENDATIONS

# Lists the 10 games that best match the current user based on their liked games (and that they have not already marked as liked)
@login_required(login_url='/ingresar')
def recomendaciones(request):
    recomendaciones = recomendar_juegos_para_usuario(request.user, 10)
    formatear_recomendaciones(recomendaciones)

    return render(request, "recomendaciones.html", {"recomendaciones": recomendaciones, 'STATIC_URL':settings.STATIC_URL})


# Lists the 5 games that best match the selected game
def juegos_similares(request):
    formulario = BusquedaJuego()
    recomendaciones = None
    juego_buscado = None

    if request.method == "POST":
        formulario = BusquedaJuego(request.POST)

        if formulario.is_valid():
            juego_buscado = formulario.cleaned_data["juego"]

            shelf = shelve.open(SHELF_NAME)
            scores_etiq_juegos = shelf["ScoresEtiquetasJuegos"]
            scores_info_juegos = shelf["ScoresInfoJuegos"]
            recomendaciones = recomendar_juegos_similares(scores_etiq_juegos, scores_info_juegos, juego_buscado.juego_id, 5)
            shelf.close()
            
            formatear_recomendaciones(recomendaciones)
            
    return render(request, "juegos_similares.html", {"formulario": formulario, "recomendaciones": recomendaciones, "juego_buscado": juego_buscado, 'STATIC_URL': settings.STATIC_URL})




### Helper functions for formatting results

def añadir_descripciones_whoosh(juegos):
    if juegos:
        ix = open_dir(INDEX_NAME)
        with ix.searcher() as searcher:
            for juego in juegos:
                r = searcher.document(juego_id=str(juego.juego_id))
                juego.descripcion = r["descripcion"]

def formatear_recomendaciones(recomendaciones):
    if recomendaciones:
        scores = [s*100 for s, _ in recomendaciones]
        juegos = [j for _, j in recomendaciones]
        añadir_descripciones_whoosh(juegos)
        recomendaciones[:] = list(zip(scores, juegos))