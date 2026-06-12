from datetime import datetime
from main.models import *
from main.scraping import cargar_datos
import os, shutil
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID

BASE_DIR = os.path.dirname(__file__)
INDEX_NAME = os.path.join(BASE_DIR, "Juegos")


def populate_desarrolladores(data):
    Desarrollador.objects.all().delete()

    nombres = set()
    for item in data:
        nombres.update(item["desarrolladores"])

    objs = [Desarrollador(nombre=n) for n in nombres]
    Desarrollador.objects.bulk_create(objs)

    return Desarrollador.objects.count()


def populate_etiquetas(data):
    Etiqueta.objects.all().delete()

    nombres = set()
    for item in data:
        nombres.update(item["etiquetas"])

    objs = [Etiqueta(nombre=n) for n in nombres]
    Etiqueta.objects.bulk_create(objs)

    return Etiqueta.objects.count()


def populate_juegos(data):
    Juego.objects.all().delete()

    schema = Schema(
        juego_id=ID(stored=True, unique=True),
        titulo=TEXT(stored=True),
        descripcion=TEXT(stored=True),
        about=TEXT(stored=True),
        reviews=TEXT    # It is only indexed for search purposes, it is not stored in the retrieved document
    )

    if os.path.exists(INDEX_NAME):
        shutil.rmtree(INDEX_NAME)
    os.mkdir(INDEX_NAME)

    ix = create_in(INDEX_NAME, schema=schema)
    writer = ix.writer()

    juegos = []
    for item in data:
        # Django model
        juegos.append(Juego(
            juego_id=item["juego_id"],
            titulo=item["titulo"],
            link=item["link"],
            imagen=item["imagen"],
            fecha=item["fecha"],
            peak_jugadores=item["peak_jugadores"],
            precio=item["precio"]
        ))
        # Whoosh index (text fields only)
        writer.add_document(
            juego_id=str(item["juego_id"]),
            titulo=item["titulo"],
            descripcion=item["descripcion"],
            about=item["about"],
            reviews="\n".join(item["reviews"])
        )
    Juego.objects.bulk_create(juegos)
    writer.commit()

    # Many2Many
    for item in data:
        juego_obj = Juego.objects.get(juego_id=item["juego_id"])
        desarrolladores_objs = [Desarrollador.objects.get(nombre=d) for d in item["desarrolladores"]]
        etiquetas_objs = [Etiqueta.objects.get(nombre=e) for e in item["etiquetas"]]
        juego_obj.desarrolladores.set(desarrolladores_objs)
        juego_obj.etiquetas.set(etiquetas_objs)

    return Juego.objects.count()


def populate_metadata():
    Metadata.objects.all().delete()

    metadata = Metadata(
        id=1,
        ultima_carga=datetime.now()
    )
    metadata.save()


def populate():
    data = cargar_datos()
    d = populate_desarrolladores(data)
    e = populate_etiquetas(data)
    j = populate_juegos(data)
    populate_metadata()
    return (d,e,j)