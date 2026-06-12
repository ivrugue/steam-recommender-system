from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Desarrollador(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Etiqueta(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Juego(models.Model):
    juego_id = models.IntegerField(primary_key=True)
    titulo = models.CharField(max_length=200, unique=True)
    link = models.URLField()
    imagen = models.URLField()
    fecha = models.DateField(null=True, blank=True)
    peak_jugadores = models.IntegerField()
    precio = models.FloatField(null=True, blank=True)
    desarrolladores = models.ManyToManyField(Desarrollador)
    etiquetas = models.ManyToManyField(Etiqueta)
    usuarios_gustan = models.ManyToManyField(User, related_name="juegos_gustados")

    def __str__(self):
        return self.titulo
    

class Metadata(models.Model):
    ultima_carga = models.DateTimeField()

    def __str__(self):
        return str(self.ultima_carga)