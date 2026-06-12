import urllib, os, ssl
from datetime import datetime
from bs4 import BeautifulSoup

if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context 

URL_BASE = "https://steamcharts.com"
TOP_GAMES_PAGE = "/top/p."
NUM_PAGINAS = 16    # There are 25 games/page

BASE_DIR = os.path.dirname(__file__)
INDEX_NAME = os.path.join(BASE_DIR, "Videojuegos")

def cargar_web(url):
    try:
        # Simulate a browser and bypass the age filter 
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Cookie": (
                "birthtime=473382001; "
                "lastagecheckage=1-January-1985; "
                "wants_mature_content=1"
            )
        }
        req = urllib.request.Request(url, headers=headers)
        f = urllib.request.urlopen(req)
        return f
    except urllib.error.HTTPError as e:
        print("Ocurrió un error")
        print(e.code)
    except urllib.error.URLError as e:
        print("Ocurrió un error")
        print(e.reason)


def cargar_datos():
    res = []

    for i in range(NUM_PAGINAS):
        cursor = i+1
        # List of games on SteamCharts
        html = cargar_web(URL_BASE+TOP_GAMES_PAGE+str(cursor))
        soup = BeautifulSoup(html, 'html.parser')
        for item in soup.find("table", id="top-games").tbody.find_all("tr"):
            a_titulo = item.find("td", class_="game-name").a
            titulo = str(a_titulo.string.strip())
            page = a_titulo["href"]
            juego_id = int(page.split('/')[-1]) # unique id of each game

            # Game page on SteamCharts
            html_juego = cargar_web(URL_BASE+page)
            soup_juego = BeautifulSoup(html_juego, 'html.parser')
            for stat in soup_juego.find("div", id="app-heading").find_all("div", class_="app-stat"):
                if "all-time peak" in stat.text.lower():
                    peak_jugadores = int(stat.span.string.strip())
                    break
            for a in soup_juego.find("div", id="app-links"):
                if "store" in a.string.lower():
                    link_steam = str(a["href"])
                    break
            
            # Game page on Steam
            html_steam = cargar_web(link_steam)
            soup_steam = BeautifulSoup(html_steam, 'html.parser')

            div_datos = soup_steam.find("div", class_="glance_ctn")
            # Filter out some listed "games" that don't actually exist, as they are testing platforms, mods or pirated games
            if div_datos is not None:
                # Basic data
                imagen = str(div_datos.find("img", class_="game_header_image_full")["src"])
                descripcion = str(div_datos.find("div", class_="game_description_snippet").get_text(strip=True))
                try:
                    texto_fecha = div_datos.find("div", class_="release_date").find("div", class_="date").string.strip().lower()
                    fecha = datetime.strptime(texto_fecha, "%d %b, %Y").date()
                except (ValueError, AttributeError):
                    fecha = None    # Several games with a future release date do not have a date yet
                desarrolladores = [str(a.string.strip()) for a in div_datos.find("div", id="developers_list").find_all("a")]
                etiquetas = [str(a.string.strip()) for a in div_datos.find("div", class_="popular_tags").find_all("a")]
                
                # Precio
                precio = None   # Several games that are not for sale (future releases or older versions) are not priced
                texto_precio = None
                for div_compra in soup_steam.find_all("div", class_="game_area_purchase_game"):
                    # Sometimes there are multiple purchase sections, but the one with the game price only has one class
                    if len(div_compra.get("class")) == 1:
                        div_descuento = div_compra.find("div", class_="discount_final_price")
                        if div_descuento:
                            texto_precio = div_descuento.string.strip()
                            break
                        div_precio = div_compra.find("div", class_="game_purchase_price")
                        if div_precio:
                            texto_precio = div_precio.string.strip()
                            break
                if texto_precio:
                    precio = 0. if "free" in texto_precio.lower() \
                        else float(texto_precio.replace(',','.').replace('-','0').replace('€', ''))   

                # About
                div_about = soup_steam.find("div", id="game_area_description")
                div_about.find("h2").decompose()
                about = str(div_about.get_text(separator="\n", strip=True))

                # Reviews
                link_reviews = f'https://steamcommunity.com/app/{juego_id}/reviews/?browsefilter=toprated'
                html_reviews = cargar_web(link_reviews)
                soup_reviews = BeautifulSoup(html_reviews, 'html.parser')
                reviews = []
                for div in soup_reviews.find_all("div", class_="apphub_CardTextContent"):
                    div.find("div", class_="date_posted").decompose()
                    reviews.append(str(div.get_text(separator="\n", strip=True)))

                item_data = {
                    "titulo":titulo,
                    "juego_id":juego_id,
                    "peak_jugadores":peak_jugadores,
                    "link":link_steam,
                    "imagen":imagen,
                    "descripcion":descripcion,
                    "fecha":fecha,
                    "desarrolladores":desarrolladores,
                    "etiquetas":etiquetas,
                    "precio":precio,
                    "about":about,
                    "reviews":reviews
                }
                res.append(item_data)
    return res