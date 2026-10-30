import ipaddress
from collections.abc import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import HistoricoIPAM, Subrede

MAX_SPLIT_RESULTS = 256
MAX_VISUAL_ADDRESSES = 1024


def network_for(subnet: Subrede):
    return ipaddress.ip_network(subnet.prefixo, strict=False)


def _merge_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _occupied_network_intervals(
    parent: Subrede, *, include_direct_addresses: bool = False
) -> list[tuple[int, int]]:
    parent_network = network_for(parent)
    intervals = []
    candidates = Subrede.objects.filter(cliente_id=parent.cliente_id, vrf_id=parent.vrf_id).exclude(
        pk=parent.pk
    )
    for candidate in candidates.only("prefixo"):
        try:
            candidate_network = network_for(candidate)
        except ValueError:
            continue
        if candidate_network.version == parent_network.version and candidate_network.subnet_of(
            parent_network
        ):
            intervals.append(
                (int(candidate_network.network_address), int(candidate_network.broadcast_address))
            )
    if include_direct_addresses:
        for value in parent.enderecos_ip.values_list("endereco", flat=True):
            try:
                address = ipaddress.ip_address(value)
            except ValueError:
                continue
            if address.version == parent_network.version and address in parent_network:
                numeric_address = int(address)
                intervals.append((numeric_address, numeric_address))
    return _merge_intervals(intervals)


def free_subnets(parent: Subrede, new_prefix: int, quantity: int) -> list[str]:
    parent_network = network_for(parent)
    max_prefix = parent_network.max_prefixlen
    if not parent_network.prefixlen < new_prefix <= max_prefix:
        raise ValidationError("O novo prefixo deve ser mais específico que a rede pai.")
    if not 1 <= quantity <= MAX_SPLIT_RESULTS:
        raise ValidationError(f"A quantidade deve estar entre 1 e {MAX_SPLIT_RESULTS}.")

    block_size = 1 << (max_prefix - new_prefix)
    parent_start = int(parent_network.network_address)
    parent_end = int(parent_network.broadcast_address)
    cursor = parent_start
    results = []

    def align(value):
        offset = max(value - parent_start, 0)
        return parent_start + ((offset + block_size - 1) // block_size) * block_size

    for occupied_start, occupied_end in _occupied_network_intervals(
        parent, include_direct_addresses=True
    ):
        while cursor + block_size - 1 < occupied_start and len(results) < quantity:
            results.append(str(ipaddress.ip_network((cursor, new_prefix))))
            cursor += block_size
        if len(results) >= quantity:
            return results
        if cursor <= occupied_end and cursor + block_size - 1 >= occupied_start:
            cursor = align(occupied_end + 1)

    while cursor + block_size - 1 <= parent_end and len(results) < quantity:
        results.append(str(ipaddress.ip_network((cursor, new_prefix))))
        cursor += block_size
    return results


@transaction.atomic
def allocate_subnets(
    *, parent: Subrede, new_prefix: int, quantity: int, description: str, user
) -> list[Subrede]:
    parent = (
        Subrede.objects.select_for_update()
        .select_related("cliente", "secao", "vrf", "equipamento", "vlan")
        .get(pk=parent.pk)
    )
    prefixes = free_subnets(parent, new_prefix, quantity)
    if len(prefixes) != quantity:
        raise ValidationError(
            f"Há espaço para apenas {len(prefixes)} bloco(s) /{new_prefix} disponível(is)."
        )

    created = []
    for prefix in prefixes:
        subnet = Subrede(
            cliente=parent.cliente,
            secao=parent.secao,
            vrf=parent.vrf,
            rede_pai=parent,
            prefixo=prefix,
            descricao=description or f"Sub-bloco de {parent.prefixo}",
            status="A",
            equipamento=parent.equipamento,
            vlan=parent.vlan,
            interface=parent.interface,
            localizacao=parent.localizacao,
        )
        subnet.save()
        created.append(subnet)

    HistoricoIPAM.objects.create(
        cliente=parent.cliente,
        usuario=user,
        acao="SPLIT",
        objeto_tipo="subrede",
        objeto_id=parent.pk,
        resumo=f"{parent.prefixo} dividido em {quantity} bloco(s) /{new_prefix}",
        detalhes={"rede_pai": parent.prefixo, "prefixos": prefixes},
    )
    return created


def next_free_address(subnet: Subrede) -> str | None:
    network = network_for(subnet)
    start = int(network.network_address)
    end = int(network.broadcast_address)
    if network.version == 4 and network.prefixlen <= 30:
        start += 1
        end -= 1

    intervals = _occupied_network_intervals(subnet)
    used = {
        int(ipaddress.ip_address(value))
        for value in subnet.enderecos_ip.values_list("endereco", flat=True)
    }
    cursor = start
    interval_index = 0
    while cursor <= end:
        while interval_index < len(intervals) and intervals[interval_index][1] < cursor:
            interval_index += 1
        if interval_index < len(intervals):
            occupied_start, occupied_end = intervals[interval_index]
            if occupied_start <= cursor <= occupied_end:
                cursor = occupied_end + 1
                continue
        if cursor not in used:
            return str(ipaddress.ip_address(cursor))
        cursor += 1
    return None


def visual_map(subnet: Subrede) -> list[dict]:
    network = network_for(subnet)
    if network.num_addresses > MAX_VISUAL_ADDRESSES:
        return []
    registered = {item.endereco: item for item in subnet.enderecos_ip.all()}
    child_networks = []
    candidates = Subrede.objects.filter(cliente_id=subnet.cliente_id, vrf_id=subnet.vrf_id).exclude(
        pk=subnet.pk
    )
    for candidate in candidates.only("prefixo"):
        try:
            candidate_network = network_for(candidate)
        except ValueError:
            continue
        if candidate_network.version == network.version and candidate_network.subnet_of(network):
            child_networks.append(
                (
                    int(candidate_network.network_address),
                    int(candidate_network.broadcast_address),
                    candidate_network.prefixlen,
                    candidate.prefixo,
                )
            )
    child_networks.sort(key=lambda item: item[2], reverse=True)

    cells = []
    for address in network:
        value = str(address)
        item = registered.get(value)
        kind = "free"
        label = "Disponível"
        if network.version == 4 and network.prefixlen <= 30:
            if address == network.network_address:
                kind, label = "special", "Rede"
            elif address == network.broadcast_address:
                kind, label = "special", "Broadcast"
        numeric_address = int(address)
        for child_start, child_end, _, child_prefix in child_networks:
            if child_start <= numeric_address <= child_end:
                kind, label = "subnet", f"Sub-rede {child_prefix}"
                break
        if item:
            kind = {"A": "active", "R": "reserved", "D": "disabled"}[item.status]
            label = item.hostname or item.descricao or item.get_status_display()
        cells.append({"address": value, "kind": kind, "label": label})
    return cells
