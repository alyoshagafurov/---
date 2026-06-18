from django import forms

from core.models import SiteSettings
from listings.models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        error_messages = {"name": {"required": "Укажите название категории."}}

    def clean_name(self):
        value = (self.cleaned_data["name"] or "").strip()
        if not value:
            raise forms.ValidationError("Укажите название категории.")
        return value


class RulesForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["rules_text"]
        widgets = {
            "rules_text": forms.Textarea(attrs={"rows": 16, "class": "form-control"})
        }
