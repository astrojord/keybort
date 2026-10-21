from django import forms

from .models import (
    CustomKeyboard,
    CustomKeycaps,
    CustomKit,
    CustomPlate,
    CustomStabilizer,
    CustomSwitch,
    Keycaps,
    Kit,
    Mod,
    Plate,
    Stabilizer,
    Switch,
)

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



class CustomPartForm(forms.ModelForm):
    # brand/name are optional on the models, but a part added by hand needs something to display
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("brand", "name"):
            if name in self.fields:
                self.fields[name].required = True
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs["rows"] = 3

class CustomKitForm(CustomPartForm):
    class Meta:
        model = CustomKit
        fields = '__all__'
        labels = {'pcb': 'PCB'}

class CustomSwitchForm(CustomPartForm):
    class Meta:
        model = CustomSwitch
        exclude = ['quantity']

class CustomKeycapsForm(CustomPartForm):
    class Meta:
        model = CustomKeycaps
        fields = '__all__'

class CustomPlateForm(CustomPartForm):
    class Meta:
        model = CustomPlate
        fields = '__all__'

class CustomStabilizerForm(CustomPartForm):
    class Meta:
        model = CustomStabilizer
        fields = '__all__'

class CustomKeyboardDetailsForm(CustomPartForm):
    class Meta:
        model = CustomKeyboard
        fields = ['bluetooth', 'wireless', 'notes', 'references']
