from django import forms
from django.contrib.auth.forms import AuthenticationForm

from helpdesk.models import Ticket


class UnifiedAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Usuário ou e-mail")
    remember_me = forms.BooleanField(label="Continuar conectado", required=False)


class NovoTicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("titulo", "descricao")
        widgets = {"descricao": forms.Textarea(attrs={"rows": 6})}

    def clean_titulo(self):
        titulo = self.cleaned_data["titulo"].strip()
        if len(titulo) < 5:
            raise forms.ValidationError("Informe um título com pelo menos 5 caracteres.")
        return titulo

    def clean_descricao(self):
        descricao = self.cleaned_data["descricao"].strip()
        if len(descricao) < 10:
            raise forms.ValidationError("Descreva o chamado com pelo menos 10 caracteres.")
        return descricao
