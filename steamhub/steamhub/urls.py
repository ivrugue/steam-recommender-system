"""
URL configuration for steamhub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index),
    path('index.html/', views.index),
    path('ingresar/', views.ingresar),
    path('cerrar_sesion/', views.cerrar_sesion),
    path('populate/', views.cargar_bd),
    path('sistema_recomendacion/', views.cargar_rs),
    path('juegos_gustados/', views.juegos_gustados),
    path('juegos_gratis_por_desarrollador/', views.juegos_gratis_por_desarrollador),
    path('top_10_juegos_populares/', views.top_10_juegos_populares),
    path('filtrar_juegos/', views.filtrar_juegos),
    path('buscar_juegos_texto/', views.buscar_juegos_texto),
    path('recomendaciones/', views.recomendaciones),
    path('juegos_similares/', views.juegos_similares),
]
