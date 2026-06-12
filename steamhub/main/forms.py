#encoding:utf-8
from django import forms
from main.models import *
from datetime import date
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Count
from django.contrib.auth.forms import AuthenticationForm

# Add format to AuthenticationForm
class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].widget.attrs.update({
            'class': 'form-control'
        })

        self.fields['password'].widget.attrs.update({
            'class': 'form-control'
        })


# /filtrar_juegos
class BusquedaJuegosFiltros(forms.Form):
    fecha_inicio = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        validators=[MaxValueValidator(date.today())])
    fecha_fin = forms.DateField(
        required=False, 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        validators=[MaxValueValidator(date.today())])

    precio_max = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        validators=[MinValueValidator(0)])

    etiqueta = forms.ModelChoiceField(
        queryset=Etiqueta.objects.annotate(num_juegos=Count("juego")).order_by("-num_juegos"), # ordena por etiquetas mas comunes
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Etiqueta"
    )

    ordenar_por = forms.ChoiceField(
        required=False,
        choices=[
            ('titulo', 'Orden alfabético'),
            ('fecha', 'Más recientes'),
            ('precio', 'Más baratos'),
            ('peak_jugadores', 'Más populares')
        ],
        label="Ordenar por",
        widget=forms.RadioSelect(),
        initial='titulo'
    )


# /buscar_juegos_texto
class BusquedaJuegosTexto(forms.Form):
    texto = forms.CharField(
        required=True,
        label="Texto de búsqueda",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Introduce palabras clave...'
        })
    )

    titulo = forms.BooleanField(
        required=False,
        initial=True,
        label="Título"
    )

    descripcion = forms.BooleanField(
        required=False,
        initial=True,
        label="Descripción"
    )

    about = forms.BooleanField(
        required=False,
        initial=True,
        label="About"
    )

    reviews = forms.BooleanField(
        required=False,
        initial=False,
        label="Reseñas"
    )

    tipo_busqueda = forms.ChoiceField(
        required=True,
        choices=[
            ('OR', 'Contenga alguna palabra (OR)'),
            ('AND', 'Contenga todas las palabras (AND)')
        ],
        widget=forms.RadioSelect,
        initial='OR',
        label="Tipo de búsqueda"
    )


# Liked games selector in /filtrar_juegos and /buscar_juegos_texto
class JuegosFavoritos(forms.Form):
    juegos = forms.ModelMultipleChoiceField(
        queryset=Juego.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False
    )


# /juegos_similares
class BusquedaJuego(forms.Form):
    juego = forms.ModelChoiceField(
        queryset=Juego.objects.all().order_by("titulo"),
        label="Buscar juego",
        widget=forms.Select(attrs={"class": "form-control"})
    )


    