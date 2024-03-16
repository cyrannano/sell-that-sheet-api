from django.db import models
from .photo import Photo


class PhotoSet(models.Model):
    photos = models.ManyToManyField(Photo, related_name='photosets')
    thumbnail = models.ForeignKey(Photo, on_delete=models.SET_NULL, null=True, related_name='thumbnail_photoset')
    directory_location = models.CharField(max_length=255)

    def __str__(self):
        return f"Photoset {self.id}"