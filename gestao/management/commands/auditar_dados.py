import ipaddress

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from gestao.models import Pagamento
from helpdesk.models import Ticket
from infraestrutura.models import EnderecoIP, Subrede, Vlan


class Command(BaseCommand):
    help = "Audita registros legados antes das novas restrições de integridade."

    def handle(self, *args, **options):
        problems = []

        duplicate_vlans = (
            Vlan.objects.values("cliente_id", "vlan_id")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
        )
        for row in duplicate_vlans:
            problems.append(f"VLAN duplicada: cliente={row['cliente_id']} vlan={row['vlan_id']}")
        for vlan in Vlan.objects.exclude(vlan_id__range=(1, 4094)):
            problems.append(f"VLAN fora do intervalo: id={vlan.pk} vlan={vlan.vlan_id}")
        for vlan in Vlan.objects.select_related("equipamento_origem"):
            if vlan.equipamento_origem and vlan.equipamento_origem.cliente_id != vlan.cliente_id:
                problems.append(f"VLAN com equipamento de outro cliente: id={vlan.pk}")

        parsed_subnets = {}
        for subnet in Subrede.objects.select_related("rede_pai", "equipamento", "vlan"):
            try:
                network = ipaddress.ip_network(subnet.prefixo, strict=False)
                parsed_subnets[subnet.pk] = network
            except ValueError:
                problems.append(f"Prefixo inválido: subrede={subnet.pk} prefixo={subnet.prefixo}")
                continue
            if subnet.rede_pai_id:
                try:
                    parent = ipaddress.ip_network(subnet.rede_pai.prefixo, strict=False)
                    if subnet.rede_pai.cliente_id != subnet.cliente_id or not network.subnet_of(
                        parent
                    ):
                        problems.append(f"Hierarquia inválida: subrede={subnet.pk}")
                except ValueError:
                    problems.append(f"Rede pai inválida: subrede={subnet.pk}")
            if subnet.equipamento and subnet.equipamento.cliente_id != subnet.cliente_id:
                problems.append(f"Sub-rede com equipamento de outro cliente: id={subnet.pk}")
            if subnet.vlan and subnet.vlan.cliente_id != subnet.cliente_id:
                problems.append(f"Sub-rede com VLAN de outro cliente: id={subnet.pk}")

        duplicate_ips = (
            EnderecoIP.objects.values("subrede_id", "endereco")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
        )
        for row in duplicate_ips:
            problems.append(f"IP duplicado: subrede={row['subrede_id']} endereco={row['endereco']}")
        for address in EnderecoIP.objects.select_related("subrede"):
            network = parsed_subnets.get(address.subrede_id)
            if not network:
                continue
            try:
                ip = ipaddress.ip_address(address.endereco)
                if ip not in network:
                    problems.append(
                        f"IP fora da sub-rede: id={address.pk} endereco={address.endereco}"
                    )
            except ValueError:
                problems.append(f"IP inválido: id={address.pk} endereco={address.endereco}")

        for ticket in Ticket.objects.select_related("equipamento"):
            if ticket.equipamento and ticket.equipamento.cliente_id != ticket.cliente_id:
                problems.append(f"Chamado com equipamento de outro cliente: id={ticket.pk}")

        duplicate_payments = (
            Pagamento.objects.values("cliente_id", "referencia")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
        )
        for row in duplicate_payments:
            problems.append(
                f"Pagamento duplicado: cliente={row['cliente_id']} referência={row['referencia']}"
            )

        if problems:
            for problem in problems:
                self.stderr.write(f"ERRO: {problem}")
            raise CommandError(f"Auditoria encontrou {len(problems)} problema(s).")
        self.stdout.write(self.style.SUCCESS("Auditoria concluída sem inconsistências."))
