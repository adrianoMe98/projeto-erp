import ipaddress

from django import forms
from django.core.exceptions import ValidationError

from .ipam import MAX_SPLIT_RESULTS, network_for
from .models import EnderecoIP, Subrede


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs["class"] = css_class


class SubredeForm(StyledModelForm):
    class Meta:
        model = Subrede
        fields = (
            "cliente",
            "secao",
            "vrf",
            "rede_pai",
            "prefixo",
            "descricao",
            "status",
            "gateway",
            "vlan",
            "equipamento",
            "interface",
            "localizacao",
            "observacoes",
        )
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("rede_pai")
        if parent:
            cleaned["cliente"] = parent.cliente
            cleaned["secao"] = parent.secao
            cleaned["vrf"] = parent.vrf
            self.instance.cliente = parent.cliente
            self.instance.secao = parent.secao
            self.instance.vrf = parent.vrf
        return cleaned


class SubnetSplitForm(forms.Form):
    new_prefix = forms.IntegerField(label="Novo prefixo")
    quantity = forms.IntegerField(
        label="Quantidade de blocos", min_value=1, max_value=MAX_SPLIT_RESULTS, initial=1
    )
    description = forms.CharField(label="Descrição", max_length=200, required=False)

    def __init__(self, *args, parent: Subrede, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        network = network_for(parent)
        self.fields["new_prefix"].min_value = network.prefixlen + 1
        self.fields["new_prefix"].max_value = network.max_prefixlen
        self.fields["new_prefix"].initial = min(
            network.prefixlen + (8 if network.version == 4 else 16), network.max_prefixlen
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

    def clean_new_prefix(self):
        value = self.cleaned_data["new_prefix"]
        network = network_for(self.parent)
        if not network.prefixlen < value <= network.max_prefixlen:
            raise ValidationError("Escolha um prefixo mais específico que o bloco pai.")
        return value


class EnderecoIPForm(StyledModelForm):
    class Meta:
        model = EnderecoIP
        fields = (
            "endereco",
            "hostname",
            "descricao",
            "status",
            "mac_address",
            "responsavel",
            "observacoes",
        )
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, subnet: Subrede, suggested_address=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.subrede = subnet
        if suggested_address and not self.is_bound:
            self.fields["endereco"].initial = suggested_address
        self.fields["endereco"].help_text = f"Deve pertencer ao bloco {subnet.prefixo}."

    def clean_mac_address(self):
        value = self.cleaned_data.get("mac_address", "").strip().lower().replace("-", ":")
        if value:
            parts = value.split(":")
            if len(parts) != 6 or any(
                len(part) != 2 or any(char not in "0123456789abcdef" for char in part)
                for part in parts
            ):
                raise ValidationError("Informe o MAC no formato aa:bb:cc:dd:ee:ff.")
        return value


def subnet_family(prefix):
    return ipaddress.ip_network(prefix, strict=False).version
