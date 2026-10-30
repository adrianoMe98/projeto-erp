import hashlib

from django.db import transaction

from cgnat.models import CgnatGeneration


def _tag(plan):
    return f"ERP-CGNAT:{plan.pk}"


def _short_id(plan):
    return str(plan.pk).replace("-", "")[:8]


def _comment(value):
    return " ".join(str(value).splitlines())


def render_routeros(plan, mappings, version):
    tag = _tag(plan)
    chain = f"ERP-CGNAT-{_short_id(plan)}"
    lines = [
        f"# ERP - CGNAT determinístico - RouterOS {version}",
        f"# Plano: {_comment(plan.nome)}",
        "# Revise em homologação antes de aplicar em produção.",
        "/ip firewall nat",
        f'remove [find where comment~"{tag}"]',
        f"add chain=srcnat action=jump jump-target={chain} src-address={plan.rede_privada} "
        f'out-interface={plan.interface_saida} comment="{tag} JUMP"',
    ]
    for item in mappings:
        base = (
            f"chain={chain} action=src-nat src-address={item.private_ip} "
            f"to-addresses={item.public_ip} to-ports={item.port_start}-{item.port_end}"
        )
        lines.append(f'add {base} protocol=tcp comment="{tag} {item.private_ip} TCP"')
        lines.append(f'add {base} protocol=udp comment="{tag} {item.private_ip} UDP"')
        if plan.incluir_icmp:
            icmp_comment = f"{tag} {item.private_ip} ICMP"
            lines.append(
                f"add chain={chain} action=src-nat src-address={item.private_ip} "
                f'to-addresses={item.public_ip} protocol=icmp comment="{icmp_comment}"'
            )
    lines.extend(
        [
            "",
            "# Recomendação: valide a ordem das regras e a tabela de conexões "
            "em janela de manutenção.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_iptables(plan, mappings):
    chain = f"ERP_CGNAT_{_short_id(plan).upper()}"
    lines = [
        "#!/bin/sh",
        "set -eu",
        f"# ERP - CGNAT determinístico - {_comment(plan.nome)}",
        f'CHAIN="{chain}"',
        'iptables -t nat -N "$CHAIN" 2>/dev/null || iptables -t nat -F "$CHAIN"',
        (
            f"iptables -t nat -C POSTROUTING -s {plan.rede_privada} "
            f'-o {plan.interface_saida} -j "$CHAIN" 2>/dev/null || '
            f"iptables -t nat -A POSTROUTING -s {plan.rede_privada} "
            f'-o {plan.interface_saida} -j "$CHAIN"'
        ),
    ]
    for item in mappings:
        destination = f"{item.public_ip}:{item.port_start}-{item.port_end}"
        lines.append(
            f'iptables -t nat -A "$CHAIN" -s {item.private_ip}/32 -p tcp '
            f"-j SNAT --to-source {destination}"
        )
        lines.append(
            f'iptables -t nat -A "$CHAIN" -s {item.private_ip}/32 -p udp '
            f"-j SNAT --to-source {destination}"
        )
        if plan.incluir_icmp:
            lines.append(
                f'iptables -t nat -A "$CHAIN" -s {item.private_ip}/32 -p icmp '
                f"-j SNAT --to-source {item.public_ip}"
            )
    lines.append('echo "Regras CGNAT carregadas em $CHAIN"')
    return "\n".join(lines) + "\n"


def render_nftables(plan, mappings):
    table = f"erp_cgnat_{_short_id(plan)}"
    lines = [
        "#!/bin/sh",
        "set -eu",
        f"# ERP - CGNAT determinístico - {_comment(plan.nome)}",
        f"nft delete table ip {table} 2>/dev/null || true",
        "nft -f - <<'NFT_RULESET'",
        f"table ip {table} {{",
        "    chain postrouting {",
        "        type nat hook postrouting priority srcnat; policy accept;",
    ]
    for item in mappings:
        destination = f"{item.public_ip}:{item.port_start}-{item.port_end}"
        lines.append(
            f'        oifname "{plan.interface_saida}" ip saddr {item.private_ip} '
            f"meta l4proto tcp snat to {destination}"
        )
        lines.append(
            f'        oifname "{plan.interface_saida}" ip saddr {item.private_ip} '
            f"meta l4proto udp snat to {destination}"
        )
        if plan.incluir_icmp:
            lines.append(
                f'        oifname "{plan.interface_saida}" ip saddr {item.private_ip} '
                f"ip protocol icmp snat to {item.public_ip}"
            )
    lines.extend(["    }", "}", "NFT_RULESET", f'echo "Tabela CGNAT {table} carregada"'])
    return "\n".join(lines) + "\n"


def render_configuration(plan, target, mappings):
    if target == CgnatGeneration.Target.ROUTEROS6:
        return render_routeros(plan, mappings, "6")
    if target == CgnatGeneration.Target.ROUTEROS7:
        return render_routeros(plan, mappings, "7")
    if target == CgnatGeneration.Target.IPTABLES:
        return render_iptables(plan, mappings)
    if target == CgnatGeneration.Target.NFTABLES:
        return render_nftables(plan, mappings)
    raise ValueError("Destino CGNAT não suportado.")


@transaction.atomic
def create_generation(plan, target, user=None, disponivel_cliente=True):
    plan.full_clean()
    mappings = plan.mappings
    content = render_configuration(plan, target, mappings)
    snapshot = [item.as_dict() for item in mappings]
    return CgnatGeneration.objects.create(
        plan=plan,
        target=target,
        content=content,
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        mapping_snapshot=snapshot,
        summary={
            "assinantes": len(snapshot),
            "rede_privada": plan.rede_privada,
            "rede_publica": plan.rede_publica,
            "portas_por_assinante": plan.portas_por_assinante,
            "interface_saida": plan.interface_saida,
        },
        created_by=user if getattr(user, "is_authenticated", False) else None,
        disponivel_cliente=disponivel_cliente,
    )
