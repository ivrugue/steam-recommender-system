import shelve
from main.models import *
from main.populateDB import INDEX_NAME
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser, OrGroup

SHELF_NAME = "dataRS.dat"


### COMPUTE SIMILARITIES

# Dice: score between tags
def dice_base(interseccion, total):
    if total == 0:
        return 0
    return (2 * interseccion) / total

def dice(a, b):
    return dice_base(len(a & b), len(a) + len(b))

def dice_ponderado(etiquetas_usuario, etiquetas):
    # Takes ALL tags, but weighted by their frequency among the user's liked games
    interseccion = sum(peso for etiq, peso in etiquetas_usuario.items() if etiq in etiquetas)
    total = sum(etiquetas_usuario.values()) + len(etiquetas)

    return dice_base(interseccion, total)


# Whoosh: score based on written information about games (descriptions + about sections)
def scores_whoosh(info):
    scores = {}

    ix = open_dir(INDEX_NAME)
    with ix.searcher() as searcher:
        parser = MultifieldParser(["descripcion", "about"], ix.schema, group=OrGroup)
        query = parser.parse(info)
        results = searcher.search(query, limit=None)

        if results:
            max_score = results[0].score
            for r in results:
                scores[int(r["juego_id"])] = r.score / max_score   # score normalizado

    return scores

def get_info_juegos(juegos_ids):
    info = []
    ix = open_dir(INDEX_NAME)
    with ix.searcher() as searcher:
        for juego_id in juegos_ids:
            r = searcher.document(juego_id=str(juego_id))
            info.append(r["descripcion"])
            info.append(r["about"])

    return "\n".join(info)



# GET TAGS

def get_etiquetas(juego):
    return juego.etiquetas.all().values_list("nombre", flat=True)

# User tags: {tag : number of liked games with that tag}
# Note: no user-related data is stored in the shelf because their liked games can change continuously
def crear_etiquetas_usuario(user):
    juegos_gustados = user.juegos_gustados.all()

    etiq_frecuencia = {}
    for juego in juegos_gustados:
        for etiq in get_etiquetas(juego):
            etiq_frecuencia[etiq] = etiq_frecuencia.get(etiq, 0) + 1

    return etiq_frecuencia



### PRECOMPUTE GAME SCORES

def calcular_scores_juegos():
    juegos = Juego.objects.all()

    scores_etiq = {}
    scores_info = {}
    for i, j1 in enumerate(juegos):
        print(i, j1)
        # Tag similarity
        for j2 in juegos[i+1:]:
            etiq1 = get_etiquetas(j1)
            etiq2 = get_etiquetas(j2)
            scores_etiq[(j1.juego_id, j2.juego_id)] = dice(etiq1, etiq2)

        # Description + about similarity
        scores_whoosh_juego = scores_whoosh(get_info_juegos([j1.juego_id]))
        for j2_id, score in scores_whoosh_juego.items():
            scores_info[(j1.juego_id, j2_id)] = score

    return scores_etiq, scores_info


def guardar_scores_juegos():
    shelf = shelve.open(SHELF_NAME)
    scores_etiq, scores_info = calcular_scores_juegos()
    shelf["ScoresEtiquetasJuegos"] = scores_etiq
    shelf["ScoresInfoJuegos"] = scores_info
    shelf.close()




### RECOMMENDATION

# Returns the n most similar games for a given game or user, as appropriate
def recomendar_juegos(para_usuario=True, scores_etiq_juegos=None, scores_info_juegos=None, etiquetas_usuario=None, referencia=[], n=None, alpha=0.7):
    recomendaciones = None

    if not para_usuario or (para_usuario and etiquetas_usuario):
        juegos_dict = Juego.objects.in_bulk(field_name='juego_id')

        # Computes Whoosh scores for the user
        if para_usuario:
            scores_info = scores_whoosh(get_info_juegos(referencia))

        scores_total = []
        juegos = []
        for juego_id, juego in juegos_dict.items():
            if juego_id in referencia:
                continue

            # Loads (if comparing games) or computes (if comparing with user) the scores
            if not para_usuario:
                clave = (referencia[0], juego_id)
                score_etiq = scores_etiq_juegos.get(tuple(sorted(clave)), 0)
                score_info = scores_info_juegos.get(clave, 0)
            else:
                etiquetas_juego = get_etiquetas(juego)
                score_etiq = dice_ponderado(etiquetas_usuario, etiquetas_juego)
                score_info = scores_info.get(juego_id, 0)
                
            # Assigns different weights to tag scores and textual information scores
            scores_total.append(alpha * score_etiq + (1-alpha) * score_info)   
            juegos.append(juego)

        recomendaciones = sorted(zip(scores_total,juegos), key=lambda x: x[0], reverse=True)[:n]

    return recomendaciones


def recomendar_juegos_para_usuario(user, n=None):
    etiquetas_usuario = crear_etiquetas_usuario(user)
    juegos_gustados = user.juegos_gustados.all().values_list("juego_id", flat=True)
    
    return recomendar_juegos(
        para_usuario=True,
        etiquetas_usuario=etiquetas_usuario, 
        referencia=juegos_gustados, 
        n=n)


def recomendar_juegos_similares(scores_etiq_juegos, scores_info_juegos, juego_id, n=None):
    return recomendar_juegos(
        para_usuario=False, 
        scores_etiq_juegos=scores_etiq_juegos, 
        scores_info_juegos=scores_info_juegos,
        referencia=[juego_id], 
        n=n)