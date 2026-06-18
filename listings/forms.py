from django import forms

from .models import Category, Listing


class ListingForm(forms.ModelForm):
    """Текстовые поля публикации (фото обрабатываются отдельно во вьюхе)."""

    class Meta:
        model = Listing
        fields = ["category", "title", "description"]
        error_messages = {
            "category": {"required": "Выберите Категорию"},
            "title": {"required": "Укажите название"},
            "description": {"required": "Укажите описание"},
        }

    def __init__(self, *args, require_category=True, **kwargs):
        super().__init__(*args, **kwargs)
        if not require_category:
            self.fields.pop("category")
        else:
            self.fields["category"].queryset = Category.objects.all()
            self.fields["category"].empty_label = "Выберите Категорию"
            self.fields["category"].widget.attrs["class"] = "form-control"

    def clean_title(self):
        value = (self.cleaned_data["title"] or "").strip()
        if not value:
            raise forms.ValidationError("Укажите название")
        if len(value) > 35:
            raise forms.ValidationError("Максимум 35 символов.")
        return value

    def clean_description(self):
        value = (self.cleaned_data["description"] or "").strip()
        if not value:
            raise forms.ValidationError("Укажите описание")
        return value
