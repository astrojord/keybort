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
    Profile,
    Stabilizer,
    StockKeyboard,
    StockKeycaps,
    StockKit,
    StockPlate,
    StockStabilizer,
    StockSwitch,
    Switch,
)

# ruff: noqa: RUF012
# following Django Meta subclass conventions


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


class ComboboxInput(forms.TextInput):
    template_name = 'widgets/combobox.html'

    def __init__(self, attrs=None, options=()):
        super().__init__(attrs)
        self.options = list(options)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget_attrs = context['widget']['attrs']
        if widget_attrs.get('aria-invalid'):
            widget_attrs['aria-describedby'] = f'{widget_attrs["id"]}-error'
        context['widget']['options'] = self.options
        return context


class CustomPartForm(forms.ModelForm):
    stock_model = None

    # brand/name are optional on the models, but a part added by hand needs something to display
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('brand', 'name'):
            if name in self.fields:
                self.fields[name].required = True
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['rows'] = 3
            elif type(field.widget) is forms.TextInput and self.stock_model:
                options = self.stock_values(name)
                if options:
                    field.widget = ComboboxInput(field.widget.attrs, options)

    def stock_values(self, name):
        return (
            self.stock_model.objects.exclude(**{f'{name}__isnull': True})
            .exclude(**{name: ''})
            .order_by(name)
            .values_list(name, flat=True)
            .distinct()
        )


class CustomKitForm(CustomPartForm):
    stock_model = StockKit

    class Meta:
        model = CustomKit
        fields = '__all__'
        labels = {'pcb': 'PCB'}


class CustomSwitchForm(CustomPartForm):
    stock_model = StockSwitch

    class Meta:
        model = CustomSwitch
        exclude = ['quantity']


class CustomKeycapsForm(CustomPartForm):
    stock_model = StockKeycaps

    class Meta:
        model = CustomKeycaps
        fields = '__all__'


class CustomPlateForm(CustomPartForm):
    stock_model = StockPlate

    class Meta:
        model = CustomPlate
        fields = '__all__'


class CustomStabilizerForm(CustomPartForm):
    stock_model = StockStabilizer

    class Meta:
        model = CustomStabilizer
        fields = '__all__'


class CustomKeyboardDetailsForm(CustomPartForm):
    class Meta:
        model = CustomKeyboard
        fields = ['bluetooth', 'wireless', 'notes', 'references']


class StockKitForm(CustomKitForm):
    class Meta(CustomKitForm.Meta):
        model = StockKit


class StockSwitchForm(CustomSwitchForm):
    class Meta(CustomSwitchForm.Meta):
        model = StockSwitch


class StockKeycapsForm(CustomKeycapsForm):
    class Meta(CustomKeycapsForm.Meta):
        model = StockKeycaps


class StockPlateForm(CustomPlateForm):
    class Meta(CustomPlateForm.Meta):
        model = StockPlate


class StockStabilizerForm(CustomStabilizerForm):
    class Meta(CustomStabilizerForm.Meta):
        model = StockStabilizer


class StockKeyboardDetailsForm(CustomPartForm):
    class Meta:
        model = StockKeyboard
        fields = ['bluetooth', 'wireless', 'notes', 'references']


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['default_part_source', 'keep_parts_on_delete']
