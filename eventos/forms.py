from django import forms
from .models import Media


class MediaUploadForm(forms.ModelForm):

    class Meta:
        model = Media
        fields = ["guest_name", "image"]

        widgets = {
            "guest_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Tu nombre (opcional)"
            }),
            "image": forms.FileInput(attrs={
                "class": "form-control",
                "accept": "image/*"
            }),
        }