import ipaddress
from dataclasses import asdict, dataclass

MAX_SUBSCRIBERS = 4096


@dataclass(frozen=True)
class PortMapping:
    private_ip: str
    public_ip: str
    port_start: int
    port_end: int

    def as_dict(self):
        return asdict(self)


def usable_addresses(network):
    return list(network.hosts())


def calculate_capacity(public_network, first_port, last_port, ports_per_subscriber):
    slots_per_public_ip = (last_port - first_port + 1) // ports_per_subscriber
    public_addresses = usable_addresses(public_network)
    return slots_per_public_ip, len(public_addresses) * slots_per_public_ip


def build_mappings(
    private_network,
    public_network,
    first_port,
    last_port,
    ports_per_subscriber,
    subscriber_limit=None,
):
    private_network = ipaddress.ip_network(private_network, strict=False)
    public_network = ipaddress.ip_network(public_network, strict=False)
    private_addresses = usable_addresses(private_network)
    public_addresses = usable_addresses(public_network)
    total_subscribers = subscriber_limit or len(private_addresses)
    if total_subscribers > MAX_SUBSCRIBERS:
        raise ValueError(f"O limite por plano é {MAX_SUBSCRIBERS} assinantes.")
    if total_subscribers > len(private_addresses):
        raise ValueError("O limite de assinantes excede os endereços privados disponíveis.")

    slots_per_public_ip, capacity = calculate_capacity(
        public_network, first_port, last_port, ports_per_subscriber
    )
    if slots_per_public_ip < 1:
        raise ValueError("A faixa de portas não comporta um assinante.")
    if total_subscribers > capacity:
        raise ValueError(
            f"Capacidade insuficiente: {capacity} posições para {total_subscribers} assinantes."
        )

    mappings = []
    for index, private_ip in enumerate(private_addresses[:total_subscribers]):
        public_index, slot_index = divmod(index, slots_per_public_ip)
        port_start = first_port + slot_index * ports_per_subscriber
        mappings.append(
            PortMapping(
                private_ip=str(private_ip),
                public_ip=str(public_addresses[public_index]),
                port_start=port_start,
                port_end=port_start + ports_per_subscriber - 1,
            )
        )
    return mappings
