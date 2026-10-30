from django.core.management.base import BaseCommand, CommandError

from pagamentos.models import PixCharge
from pagamentos.services.simulator import simulate_payment


class Command(BaseCommand):
    help = "Confirma uma cobrança Pix no simulador local."

    def add_arguments(self, parser):
        parser.add_argument("txid")

    def handle(self, *args, **options):
        try:
            charge = PixCharge.objects.get(txid=options["txid"])
        except PixCharge.DoesNotExist as exc:
            raise CommandError("Cobrança não encontrada.") from exc
        _, created = simulate_payment(charge)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Cobrança {charge.txid} confirmada."))
        else:
            self.stdout.write(self.style.WARNING("O evento já havia sido processado."))
