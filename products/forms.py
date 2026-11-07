from django import forms

from .models import Product, Review, Seller, Variation


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        return files.getlist(name)


class MultiFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned_files = []
        for item in data:
            cleaned_files.append(super().clean(item, initial))
        return cleaned_files

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')

    rating = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-rating-input'}),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )


class ProductSubmissionForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            'name',
            'description',
            'price',
            'stock',
            'category',
            'subcategory',
            'condition',
            'image',
        )

    seller = forms.ModelChoiceField(
        queryset=Seller.objects.order_by('store_name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )
    price = forms.DecimalField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    stock = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    category = forms.ModelChoiceField(
        queryset=Product._meta.get_field('category').remote_field.model.objects.order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    subcategory = forms.ModelChoiceField(
        queryset=Product._meta.get_field('subcategory').remote_field.model.objects.order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    condition = forms.ChoiceField(
        choices=Product.CONDITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    image = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    extra_images = MultiFileField(
        required=False,
        widget=MultiFileInput(attrs={'class': 'form-control', 'multiple': True}),
        help_text='You can select multiple images.',
    )

    def __init__(self, *args, **kwargs):
        show_seller = kwargs.pop('show_seller', False)
        super().__init__(*args, **kwargs)
        if not show_seller:
            self.fields.pop('seller', None)


class VariationForm(forms.ModelForm):
    class Meta:
        model = Variation
        fields = ('name', 'value', 'price_modifier', 'stock', 'is_active')

    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    value = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    price_modifier = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    stock = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    is_active = forms.BooleanField(required=False)

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get('name') or '').strip()
        value = (cleaned.get('value') or '').strip()
        if name or value:
            if not name or not value:
                raise forms.ValidationError('Variation name and value are both required.')
        return cleaned


VariationFormSet = forms.formset_factory(VariationForm, extra=3, can_delete=True, min_num=0, validate_min=False)
