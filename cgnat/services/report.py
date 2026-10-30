from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_generation_pdf(generation):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Relatório CGNAT - {generation.plan.nome}",
        author="ERP de Consultoria",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            textColor=colors.HexColor("#0f3d63"),
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSmall",
            parent=styles["BodyText"],
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#536777"),
        )
    )

    plan = generation.plan
    story = [
        Paragraph("RELATÓRIO DE ALOCAÇÃO CGNAT", styles["ReportTitle"]),
        Paragraph(escape(plan.cliente.nome_fantasia), styles["Heading2"]),
        Spacer(1, 0.2 * cm),
    ]
    metadata = [
        ["Plano", plan.nome, "Destino", generation.get_target_display()],
        ["Rede privada", plan.rede_privada, "Rede pública", plan.rede_publica],
        [
            "Portas/assinante",
            str(plan.portas_por_assinante),
            "Assinantes",
            str(len(generation.mapping_snapshot)),
        ],
        [
            "Interface",
            plan.interface_saida,
            "Gerado em",
            generation.created_at.strftime("%d/%m/%Y %H:%M"),
        ],
    ]
    metadata_table = Table(metadata, colWidths=[3.2 * cm, 5.7 * cm, 3.2 * cm, 5.7 * cm])
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1f8")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#e8f1f8")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9fb3c4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            metadata_table,
            Spacer(1, 0.35 * cm),
            Paragraph(
                "Cada endereço interno possui um endereço público e uma faixa de portas exclusiva. "
                "Essa correspondência deve ser preservada para rastreabilidade operacional.",
                styles["BodyText"],
            ),
            Spacer(1, 0.35 * cm),
        ]
    )

    mapping_rows = [["IP interno", "IP público", "Porta inicial", "Porta final"]]
    mapping_rows.extend(
        [
            item["private_ip"],
            item["public_ip"],
            str(item["port_start"]),
            str(item["port_end"]),
        ]
        for item in generation.mapping_snapshot
    )
    mapping_table = LongTable(
        mapping_rows,
        repeatRows=1,
        colWidths=[5.1 * cm, 5.1 * cm, 4.1 * cm, 4.1 * cm],
    )
    mapping_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d63")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f8")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b7c5d0")),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            mapping_table,
            Spacer(1, 0.3 * cm),
            Paragraph(f"SHA-256 da configuração: {generation.sha256}", styles["ReportSmall"]),
            Paragraph(
                "Documento de apoio operacional. Valide a configuração no ambiente "
                "de homologação antes da implantação.",
                styles["ReportSmall"],
            ),
        ]
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#536777"))
        canvas.drawString(1.5 * cm, 0.9 * cm, "ERP de Consultoria - Relatório CGNAT")
        canvas.drawRightString(A4[0] - 1.5 * cm, 0.9 * cm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
