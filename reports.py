# reports.py

from io import BytesIO
from flask import make_response
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from datetime import datetime
import logging
import locale

# Importar modelos necessários para TIPO_ITEM_CHOICES e outros detalhes se necessário
from models import ItemAta 

# Configuração básica do logger
logger = logging.getLogger(__name__)

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---
def _format_br_currency_pdf(value):
    """Formata um valor numérico para o padrão monetário brasileiro para PDFs."""
    if value is None:
        return "R$ 0,00"
    try:
        num_value = float(value)
        current_locale_monetary = locale.getlocale(locale.LC_MONETARY)
        current_locale_numeric = locale.getlocale(locale.LC_NUMERIC)
        
        locale_set = False
        for loc_str in ['pt_BR.UTF-8', 'Portuguese_Brazil.1252', 'ptb']:
            try:
                locale.setlocale(locale.LC_ALL, loc_str)
                locale_set = True
                break
            except locale.Error:
                continue
        
        if not locale_set: 
            formatted_fallback = f"{num_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            # Restaura locale apenas se não for (None,None) para evitar erro no setlocale
            if current_locale_monetary != (None, None) and current_locale_monetary[0] is not None:
                 try: locale.setlocale(locale.LC_MONETARY, current_locale_monetary)
                 except: pass
            if current_locale_numeric != (None, None) and current_locale_numeric[0] is not None:
                 try: locale.setlocale(locale.LC_NUMERIC, current_locale_numeric)
                 except: pass
            return f"R$ {formatted_fallback}"
        
        formatted = locale.currency(num_value, symbol=True, grouping=True, international=False)
        
        if current_locale_monetary != (None, None) and current_locale_monetary[0] is not None:
            try: locale.setlocale(locale.LC_MONETARY, current_locale_monetary)
            except: pass
        if current_locale_numeric != (None, None) and current_locale_numeric[0] is not None:
            try: locale.setlocale(locale.LC_NUMERIC, current_locale_numeric)
            except: pass
        return formatted
    except (ValueError, TypeError):
        return str(value) 

def _format_qty_pdf(value):
    """Formata uma quantidade para PDF. Inteiro se for inteiro, senão com 2 decimais e vírgula."""
    if value is None:
        return "-"
    try:
        num_value = float(value)
        if num_value == int(num_value): 
            return str(int(num_value))
        else: 
            return f"{num_value:.2f}".replace('.', ',')
    except (ValueError, TypeError):
        return str(value)

# --- TEMPLATE DE PÁGINA (CABEÇALHO/RODAPÉ) ---
def _my_page_template(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    page_num_text = f"Página {doc.page}"
    # Ajuste para margens e orientação
    canvas.drawRightString(doc.width + doc.leftMargin - 0.5*inch, 0.5*inch, page_num_text)
    canvas.restoreState()

# --- FUNÇÕES DE GERAÇÃO DE PDF ---
def gerar_pdf_lista_atas(todas_as_atas):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=1*inch, bottomMargin=1*inch)
    styles = getSampleStyleSheet()
    story = []

    style_titulo = ParagraphStyle(name='TituloRelatorio', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=0.3*inch)
    style_info_header = ParagraphStyle(name='InfoRelatorio', parent=styles['Normal'], fontSize=10, spaceBefore=0.1*inch, spaceAfter=0.2*inch, alignment=0) 
    style_table_header = ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
    style_table_cell = ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=9, leading=11)

    story.append(Paragraph("Relatório - Listagem de Atas de Registro de Preço", style_titulo))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", style_info_header))
    story.append(Spacer(1, 0.2*inch))

    if not todas_as_atas:
        story.append(Paragraph("Nenhuma ata registrada para exibir.", styles['Normal']))
    else:
        table_data = [
            [Paragraph("Nº Ata/Ano", style_table_header),
             Paragraph("Descrição", style_table_header),
             Paragraph("Assinatura", style_table_header),
             Paragraph("Validade", style_table_header)]
        ]

        for ata in todas_as_atas:
            table_data.append([
                Paragraph(f"{ata.numero_ata}/{ata.ano}", style_table_cell),
                Paragraph(ata.descricao if ata.descricao else '-', style_table_cell),
                Paragraph(ata.data_assinatura.strftime('%d/%m/%Y') if ata.data_assinatura else '-', style_table_cell),
                Paragraph(ata.data_validade.strftime('%d/%m/%Y') if ata.data_validade else '-', style_table_cell)
            ])
        
        col_widths = [1.5*inch, 3.3*inch, 1.2*inch, 1.2*inch] 
        
        ata_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_table = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), 
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ])
        ata_table.setStyle(style_table)
        story.append(ata_table)

    try:
        doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    except Exception as e:
        logger.error(f"Erro ao construir PDF da lista de atas: {e}", exc_info=True)
        raise
        
    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_lista_atas.pdf'
    return response

def gerar_pdf_detalhes_ata(ata, itens_da_ata):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=1*inch, bottomMargin=1*inch)
    styles = getSampleStyleSheet()
    story = []

    style_titulo = ParagraphStyle(name='TituloRelatorio', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=0.2*inch)
    style_subtitulo = ParagraphStyle(name='Subtitulo', parent=styles['h2'], fontSize=12, spaceBefore=0.2*inch, spaceAfter=0.1*inch, alignment=0)
    style_info_ata = ParagraphStyle(name='InfoAta', parent=styles['Normal'], fontSize=10, spaceAfter=0.05*inch, leading=12)
    style_info_header = ParagraphStyle(name='InfoRelatorio', parent=styles['Normal'], fontSize=10, spaceBefore=0.1*inch, spaceAfter=0.2*inch, alignment=0)
    style_table_header = ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8)
    style_table_cell = ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=8, leading=10)
    style_table_cell_right = ParagraphStyle(name='TableCellRight', parent=style_table_cell, alignment=2) 

    story.append(Paragraph(f"Relatório - Detalhes da Ata Nº {ata.numero_ata}/{ata.ano}", style_titulo))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", style_info_header))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph(f"<b>Número da Ata:</b> {ata.numero_ata}/{ata.ano}", style_info_ata))
    if ata.descricao:
        story.append(Paragraph(f"<b>Descrição:</b> {ata.descricao}", style_info_ata))
    if ata.data_assinatura:
        story.append(Paragraph(f"<b>Data de Assinatura:</b> {ata.data_assinatura.strftime('%d/%m/%Y')}", style_info_ata))
    if ata.data_validade:
        story.append(Paragraph(f"<b>Data de Validade:</b> {ata.data_validade.strftime('%d/%m/%Y')}", style_info_ata))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Itens da Ata:", style_subtitulo))

    if not itens_da_ata:
        story.append(Paragraph("Nenhum item registrado para esta ata.", styles['Normal']))
    else:
        tipo_item_map = dict(ItemAta.TIPO_ITEM_CHOICES) 
        header_content = ["Item", "Tipo", "Un.", "Qtd. Reg.", "Saldo Disp.", "Vlr. Unit.", "Lote"]
        table_data = [[Paragraph(text, style_table_header) for text in header_content]]
        
        for item in itens_da_ata:
            table_data.append([
                Paragraph(item.descricao_item, style_table_cell),
                Paragraph(tipo_item_map.get(item.tipo_item, str(item.tipo_item)), style_table_cell),
                Paragraph(item.unidade_medida if item.unidade_medida else '-', style_table_cell),
                Paragraph(_format_qty_pdf(item.quantidade_registrada), style_table_cell_right),
                Paragraph(_format_qty_pdf(item.saldo_disponivel), style_table_cell_right),
                Paragraph(_format_br_currency_pdf(item.valor_unitario_registrado), style_table_cell_right),
                Paragraph(item.lote if item.lote else '-', style_table_cell)
            ])
        
        col_widths = [2.0*inch, 0.9*inch, 0.4*inch, 0.8*inch, 0.8*inch, 1.0*inch, 0.8*inch] 
        
        item_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_item_table = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ])
        item_table.setStyle(style_item_table)
        story.append(item_table)

    try:
        doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    except Exception as e:
        logger.error(f"Erro ao construir PDF de detalhes da ata {ata.id}: {e}", exc_info=True)
        raise

    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=rel_detalhes_ata_{ata.numero_ata}_{ata.ano}.pdf'
    return response

def gerar_pdf_consumo_por_unidade(unidade, dados_consumo, data_inicio_filtro, data_fim_filtro):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.75*inch, bottomMargin=1*inch) 
    
    styles = getSampleStyleSheet()
    story = []

    style_titulo = ParagraphStyle(name='TituloRelatorio', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=0.2*inch)
    style_info_header = ParagraphStyle(name='InfoCabecalho', parent=styles['Normal'], fontSize=10, spaceAfter=0.1*inch, leading=12)
    style_total_geral = ParagraphStyle(name='TotalGeral', parent=styles['Normal'], fontSize=11, alignment=2, spaceBefore=0.2*inch, leading=14, fontName='Helvetica-Bold')
    style_table_header = ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8)
    style_table_cell = ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=8, leading=10)
    style_table_cell_right = ParagraphStyle(name='TableCellRight', parent=style_table_cell, alignment=2)


    titulo_txt = f"Relatório de Consumo - Unidade: {unidade.nome_unidade}"
    story.append(Paragraph(titulo_txt, style_titulo))

    periodo_str = "Todo o período"
    if data_inicio_filtro and data_fim_filtro:
        periodo_str = f"Período: {data_inicio_filtro.strftime('%d/%m/%Y')} a {data_fim_filtro.strftime('%d/%m/%Y')}"
    elif data_inicio_filtro:
        periodo_str = f"Período: A partir de {data_inicio_filtro.strftime('%d/%m/%Y')}"
    elif data_fim_filtro:
        periodo_str = f"Período: Até {data_fim_filtro.strftime('%d/%m/%Y')}"
    
    story.append(Paragraph(periodo_str, style_info_header))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", style_info_header))
    story.append(Spacer(1, 0.2*inch))

    if not dados_consumo:
        story.append(Paragraph("Nenhum dado de consumo encontrado para os filtros selecionados.", styles['Normal']))
    else:
        header_content = ["Item Consumido", "Tipo", "Un.", "Ata Origem", "Doc. Origem", "Data Doc.", "Qtd. Cons.", "Valor Total"]
        table_data = [[Paragraph(text, style_table_header) for text in header_content]]
        
        valor_total_geral_consumido = 0.0

        for consumo in dados_consumo:
            table_data.append([
                Paragraph(consumo.get('item_descricao', '-'), style_table_cell),
                Paragraph(str(consumo.get('item_tipo', '-')), style_table_cell),
                Paragraph(str(consumo.get('item_unidade', '-')), style_table_cell),
                Paragraph(str(consumo.get('ata_origem', '-')), style_table_cell),
                Paragraph(str(consumo.get('documento_origem', '-')), style_table_cell),
                Paragraph(str(consumo.get('data_documento', '-')), style_table_cell),
                Paragraph(_format_qty_pdf(consumo.get('quantidade_consumida', 0)), style_table_cell_right),
                Paragraph(_format_br_currency_pdf(consumo.get('valor_total_consumido', 0.0)), style_table_cell_right)
            ])
            valor_total_geral_consumido += consumo.get('valor_total_consumido', 0.0)

        col_widths = [2.4*inch, 0.9*inch, 0.4*inch, 1.0*inch, 1.4*inch, 0.9*inch, 0.8*inch, 1.0*inch]

        consumo_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_table = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'), 
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ])
        consumo_table.setStyle(style_table)
        story.append(consumo_table)
        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph(f"Valor Total Geral Consumido: {_format_br_currency_pdf(valor_total_geral_consumido)}", style_total_geral))

    try:
        doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    except Exception as e:
        logger.error(f"Erro ao construir PDF de consumo por unidade: {e}", exc_info=True)
        raise 

    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    nome_arquivo_unidade = "".join(c if c.isalnum() else "_" for c in unidade.nome_unidade)
    response.headers['Content-Disposition'] = f'inline; filename=rel_consumo_{nome_arquivo_unidade.lower()}.pdf'
    
    return response

def gerar_pdf_consumo_por_item(item_selecionado, dados_consumo_agregado_por_unidade, data_inicio_filtro, data_fim_filtro):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=1*inch, bottomMargin=1*inch)
    styles = getSampleStyleSheet()
    story = []

    style_titulo = ParagraphStyle(name='TituloRelatorio', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=0.2*inch)
    style_subtitulo = ParagraphStyle(name='Subtitulo', parent=styles['h2'], fontSize=12, spaceBefore=0.2*inch, spaceAfter=0.1*inch, alignment=0)
    style_info_header = ParagraphStyle(name='InfoCabecalho', parent=styles['Normal'], fontSize=10, spaceAfter=0.05*inch, leading=12)
    style_info_geral = ParagraphStyle(name='InfoGeral', parent=styles['Normal'], fontSize=10, spaceBefore=0.1*inch, spaceAfter=0.1*inch, fontName='Helvetica-Bold')
    style_table_header = ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
    style_table_cell = ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=9, leading=11)
    style_table_cell_right = ParagraphStyle(name='TableCellRight', parent=style_table_cell, alignment=2)

    story.append(Paragraph("Relatório de Consumo por Item Específico", style_titulo))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph(f"<b>Item:</b> {item_selecionado.descricao_item}", style_info_header))
    tipo_item_map = dict(ItemAta.TIPO_ITEM_CHOICES)
    story.append(Paragraph(f"<b>Tipo:</b> {tipo_item_map.get(item_selecionado.tipo_item, item_selecionado.tipo_item)}", style_info_header))
    story.append(Paragraph(f"<b>Unidade de Medida (Ata):</b> {item_selecionado.unidade_medida or '-'}", style_info_header))
    if item_selecionado.ata_mae:
        story.append(Paragraph(f"<b>Ata de Origem:</b> {item_selecionado.ata_mae.numero_ata}/{item_selecionado.ata_mae.ano}", style_info_header))
    
    periodo_str = "Todo o período"
    if data_inicio_filtro and data_fim_filtro:
        periodo_str = f"Consumo de {data_inicio_filtro.strftime('%d/%m/%Y')} a {data_fim_filtro.strftime('%d/%m/%Y')}"
    elif data_inicio_filtro:
        periodo_str = f"Consumo a partir de {data_inicio_filtro.strftime('%d/%m/%Y')}"
    elif data_fim_filtro:
        periodo_str = f"Consumo até {data_fim_filtro.strftime('%d/%m/%Y')}"
    story.append(Paragraph(f"<b>Período Analisado:</b> {periodo_str}", style_info_header))
    story.append(Spacer(1, 0.2*inch))

    total_geral_qtd_consumida = sum(d.get('total_qtd', 0.0) for d in dados_consumo_agregado_por_unidade)
    total_geral_valor_consumido = sum(d.get('total_valor', 0.0) for d in dados_consumo_agregado_por_unidade)

    story.append(Paragraph(f"Quantidade Total Consumida do Item: {_format_qty_pdf(total_geral_qtd_consumida)}", style_info_geral))
    story.append(Paragraph(f"Valor Total Consumido do Item: {_format_br_currency_pdf(total_geral_valor_consumido)}", style_info_geral))
    story.append(Spacer(1, 0.2*inch))

    if not dados_consumo_agregado_por_unidade:
        story.append(Paragraph("Nenhum consumo encontrado para este item nos filtros selecionados.", styles['Normal']))
    else:
        story.append(Paragraph("Detalhamento do Consumo por Unidade de Saúde:", style_subtitulo))
        
        header_content_unidade = ["Unidade de Saúde", "Qtd. Consumida", "Valor Total Consumido"]
        table_data_unidade = [[Paragraph(text, style_table_header) for text in header_content_unidade]]

        for dados_unidade in dados_consumo_agregado_por_unidade:
            table_data_unidade.append([
                Paragraph(dados_unidade.get('nome_unidade', '-'), style_table_cell),
                Paragraph(_format_qty_pdf(dados_unidade.get('total_qtd', 0)), style_table_cell_right),
                Paragraph(_format_br_currency_pdf(dados_unidade.get('total_valor', 0.0)), style_table_cell_right)
            ])
        
        col_widths_unidade = [3.5*inch, 1.5*inch, 2.0*inch]
        consumo_unidade_table = Table(table_data_unidade, colWidths=col_widths_unidade, repeatRows=1)
        style_table_unidade = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 3),
        ])
        consumo_unidade_table.setStyle(style_table_unidade)
        story.append(consumo_unidade_table)

    try:
        doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    except Exception as e:
        logger.error(f"Erro ao construir PDF de consumo do item {item_selecionado.id}: {e}", exc_info=True)
        raise

    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    nome_arquivo_item = "".join(c if c.isalnum() else "_" for c in item_selecionado.descricao_item[:30])
    response.headers['Content-Disposition'] = f'inline; filename=rel_consumo_item_{nome_arquivo_item.lower()}.pdf'
    
    return response