from django import forms

from .models import Kit, Keycaps, Switch, Stabilizer, Plate, Mod

class KitForm(forms.ModelForm):
    class Meta:
        model = Kit
        fields = '__all__'

class KeycapsForm(forms.ModelForm):
    class Meta:
        model = Keycaps
        fields = '__all__'

class SwitchForm(forms.ModelForm):
    class Meta:
        model = Switch
        fields = '__all__'

class StabilizerForm(forms.ModelForm):
    class Meta:
        model = Stabilizer
        fields = '__all__'

class PlateForm(forms.ModelForm):
    class Meta:
        model = Plate
        fields = '__all__'

class ModForm(forms.ModelForm):
    class Meta:
        model = Mod
        fields = '__all__'

