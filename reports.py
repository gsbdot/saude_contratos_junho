# Início do arquivo completo: reports.py
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

# --- MODIFICAÇÃO: Importar o modelo Processo ---
from models import ItemAta, Contrato, Contratinho, Empenho, Processo

logger = logging.getLogger(__name__)

# --- FUNÇÕES AUXILIARES DE FORMATAÇÃO ---
def _format_br_currency_pdf(value):
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
    canvas.drawRightString(doc.width + doc.leftMargin - 0.5*inch, 0.5*inch, page_num_text)
    canvas.restoreState()

# --- ESTILOS PADRÃO ---
def get_default_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TituloRelatorio', parent=styles['h1'], alignment=1, fontSize=16, spaceAfter=0.2*inch))
    styles.add(ParagraphStyle(name='Subtitulo', parent=styles['h2'], fontSize=12, spaceBefore=0.2*inch, spaceAfter=0.1*inch, alignment=0))
    styles.add(ParagraphStyle(name='InfoGeral', parent=styles['Normal'], fontSize=10, spaceAfter=0.05*inch, leading=12))
    styles.add(ParagraphStyle(name='InfoData', parent=styles['Normal'], fontSize=9, spaceAfter=0.2*inch, alignment=0))
    styles.add(ParagraphStyle(name='TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8))
    styles.add(ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='TableCellRight', parent=styles['Normal'], alignment=2, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='CommentHeader', parent=styles['h3'], fontSize=11, spaceBefore=0.2*inch, spaceAfter=0.1*inch))
    styles.add(ParagraphStyle(name='CommentUser', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9))
    styles.add(ParagraphStyle(name='CommentContent', parent=styles['Normal'], fontSize=9, leftIndent=15, leading=11))
    return styles

# --- FUNÇÕES DE GERAÇÃO DE PDF ---
def gerar_pdf_lista_atas(todas_as_atas):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=1*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph("Relatório - Listagem de Atas de Registro de Preço", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))

    table_data = [
        [Paragraph("Nº Ata/Ano", styles['TableHeader']),
         Paragraph("Descrição", styles['TableHeader']),
         Paragraph("Assinatura", styles['TableHeader']),
         Paragraph("Validade", styles['TableHeader'])]
    ]

    for ata in todas_as_atas:
        table_data.append([
            Paragraph(f"{ata.numero_ata}/{ata.ano}", styles['TableCell']),
            Paragraph(ata.descricao if ata.descricao else '-', styles['TableCell']),
            Paragraph(ata.data_assinatura.strftime('%d/%m/%Y') if ata.data_assinatura else '-', styles['TableCell']),
            Paragraph(ata.data_validade.strftime('%d/%m/%Y') if ata.data_validade else '-', styles['TableCell'])
        ])
    
    ata_table = Table(table_data, colWidths=[1.5*inch, 3.3*inch, 1.2*inch, 1.2*inch], repeatRows=1)
    ata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(ata_table)

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_lista_atas.pdf'
    return response

def gerar_pdf_detalhes_ata(ata, itens_da_ata):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=1*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph(f"Relatório - Detalhes da Ata Nº {ata.numero_ata}/{ata.ano}", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))
    
    story.append(Paragraph(f"<b>Número da Ata:</b> {ata.numero_ata}/{ata.ano}", styles['InfoGeral']))
    if ata.descricao: story.append(Paragraph(f"<b>Descrição:</b> {ata.descricao}", styles['InfoGeral']))
    if ata.data_assinatura: story.append(Paragraph(f"<b>Data de Assinatura:</b> {ata.data_assinatura.strftime('%d/%m/%Y')}", styles['InfoGeral']))
    if ata.data_validade: story.append(Paragraph(f"<b>Data de Validade:</b> {ata.data_validade.strftime('%d/%m/%Y')}", styles['InfoGeral']))
    
    story.append(Paragraph("Itens da Ata:", styles['Subtitulo']))

    if len(itens_da_ata) > 0:
        tipo_item_map = dict(ItemAta.TIPO_ITEM_CHOICES) 
        header_content = ["Item", "Tipo", "Un.", "Qtd. Reg.", "Saldo Disp.", "Vlr. Unit.", "Lote"]
        table_data = [[Paragraph(text, styles['TableHeader']) for text in header_content]]
        
        for item in itens_da_ata:
            table_data.append([
                Paragraph(item.descricao_item, styles['TableCell']),
                Paragraph(tipo_item_map.get(item.tipo_item, str(item.tipo_item)), styles['TableCell']),
                Paragraph(item.unidade_medida if item.unidade_medida else '-', styles['TableCell']),
                Paragraph(_format_qty_pdf(item.quantidade_registrada), styles['TableCellRight']),
                Paragraph(_format_qty_pdf(item.saldo_disponivel), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(item.valor_unitario_registrado), styles['TableCellRight']),
                Paragraph(item.lote if item.lote else '-', styles['TableCell'])
            ])
        
        item_table = Table(table_data, colWidths=[2.0*inch, 0.9*inch, 0.4*inch, 0.8*inch, 0.8*inch, 1.0*inch, 0.8*inch], repeatRows=1)
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(item_table)
    else:
        story.append(Paragraph("Nenhum item registrado para esta ata.", styles['Normal']))

    if ata.comments.count() > 0:
        story.append(Paragraph("Comentários", styles['Subtitulo']))
        for comment in ata.comments:
            story.append(Paragraph(f"{comment.author.username} em {comment.timestamp.strftime('%d/%m/%Y %H:%M')}:", styles['CommentUser']))
            story.append(Paragraph(comment.content.replace('\n', '<br/>'), styles['CommentContent']))
            story.append(Spacer(1, 0.1*inch))

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=rel_detalhes_ata_{ata.numero_ata}_{ata.ano}.pdf'
    return response

def gerar_pdf_detalhes_contrato(contrato):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=1*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph(f"Detalhes do Contrato Nº {contrato.numero_contrato}", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))
    story.append(Paragraph(f"<b>Objeto:</b> {contrato.objeto}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Fornecedor:</b> {contrato.fornecedor or 'Não informado'}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Vigência:</b> {contrato.data_inicio_vigencia.strftime('%d/%m/%Y') if contrato.data_inicio_vigencia else '?'} a {contrato.data_fim_vigencia.strftime('%d/%m/%Y') if contrato.data_fim_vigencia else '?'}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Valor Global:</b> {_format_br_currency_pdf(contrato.valor_global_contrato)}", styles['InfoGeral']))

    if contrato.itens_do_contrato.count() > 0:
        story.append(Paragraph("Itens do Contrato", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Item", "Un.", "Qtd.", "Vlr. Unit.", "Vlr. Total"]]]
        for item in contrato.itens_do_contrato:
            data.append([
                Paragraph(item.descricao, styles['TableCell']),
                Paragraph(item.unidade_medida or '-', styles['TableCell']),
                Paragraph(_format_qty_pdf(item.quantidade), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(item.valor_unitario), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(item.valor_total_item), styles['TableCellRight']),
            ])
        t = Table(data, colWidths=[3.2*inch, 0.5*inch, 0.8*inch, 1.2*inch, 1.2*inch], repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t)

    if contrato.aditivos.count() > 0:
        story.append(Paragraph("Termos Aditivos", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Número", "Data", "Acréscimo Valor", "Acréscimo Prazo", "Nova Vigência"]]]
        for aditivo in contrato.aditivos:
            data.append([
                Paragraph(aditivo.numero_aditivo, styles['TableCell']),
                Paragraph(aditivo.data_assinatura.strftime('%d/%m/%Y'), styles['TableCell']),
                Paragraph(_format_br_currency_pdf(aditivo.valor_acrescimo), styles['TableCellRight']),
                Paragraph(f"{aditivo.prazo_adicional_dias} dias" if aditivo.prazo_adicional_dias else '-', styles['TableCellRight']),
                Paragraph(aditivo.nova_data_fim_vigencia.strftime('%d/%m/%Y') if aditivo.nova_data_fim_vigencia else '-', styles['TableCell']),
            ])
        t = Table(data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1.5*inch, 1.5*inch], repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t)

    if contrato.comments.count() > 0:
        story.append(Paragraph("Comentários", styles['Subtitulo']))
        for comment in contrato.comments:
            story.append(Paragraph(f"{comment.author.username} em {comment.timestamp.strftime('%d/%m/%Y %H:%M')}:", styles['CommentUser']))
            story.append(Paragraph(comment.content.replace('\n', '<br/>'), styles['CommentContent']))
            story.append(Spacer(1, 0.1*inch))
    
    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()
    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=contrato_{contrato.numero_contrato.replace("/", "-")}.pdf'
    return response

def gerar_pdf_detalhes_contratinho(contratinho):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=1*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph(f"Detalhes do Contratinho Nº {contratinho.numero_contratinho}", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))
    story.append(Paragraph(f"<b>Favorecido:</b> {contratinho.favorecido or 'Não informado'}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Ata Vinculada:</b> {contratinho.ata_vinculada.numero_ata}/{contratinho.ata_vinculada.ano}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Unidade:</b> {contratinho.unidade_saude_solicitante.nome_unidade if contratinho.unidade_saude_solicitante else 'N/A'}", styles['InfoGeral']))
    
    if contratinho.itens_consumidos.count() > 0:
        story.append(Paragraph("Itens Consumidos", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Item", "Un.", "Qtd. Consumida", "Vlr. Unit.", "Vlr. Total"]]]
        for consumo in contratinho.itens_consumidos:
            data.append([
                Paragraph(consumo.item_ata_consumido.descricao_item, styles['TableCell']),
                Paragraph(consumo.item_ata_consumido.unidade_medida or '-', styles['TableCell']),
                Paragraph(_format_qty_pdf(consumo.quantidade_consumida), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(consumo.valor_unitario_no_consumo), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(consumo.valor_total_consumido_item), styles['TableCellRight']),
            ])
        t = Table(data, colWidths=[3.2*inch, 0.5*inch, 1*inch, 1.1*inch, 1.1*inch], repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t)

    if contratinho.comments.count() > 0:
        story.append(Paragraph("Comentários", styles['Subtitulo']))
        for comment in contratinho.comments:
            story.append(Paragraph(f"{comment.author.username} em {comment.timestamp.strftime('%d/%m/%Y %H:%M')}:", styles['CommentUser']))
            story.append(Paragraph(comment.content.replace('\n', '<br/>'), styles['CommentContent']))
            story.append(Spacer(1, 0.1*inch))

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()
    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=contratinho_{contratinho.numero_contratinho.replace("/", "-")}.pdf'
    return response

def gerar_pdf_detalhes_empenho(empenho):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=1*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph(f"Detalhes do Empenho Nº {empenho.numero_empenho}", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))
    story.append(Paragraph(f"<b>Favorecido:</b> {empenho.favorecido or 'Não informado'}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Ata Vinculada:</b> {empenho.ata_vinculada.numero_ata}/{empenho.ata_vinculada.ano}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Unidade:</b> {empenho.unidade_saude_solicitante.nome_unidade if empenho.unidade_saude_solicitante else 'N/A'}", styles['InfoGeral']))
    
    if empenho.itens_consumidos.count() > 0:
        story.append(Paragraph("Itens Consumidos", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Item", "Un.", "Qtd. Consumida", "Vlr. Unit.", "Vlr. Total"]]]
        for consumo in empenho.itens_consumidos:
            data.append([
                Paragraph(consumo.item_ata_consumido.descricao_item, styles['TableCell']),
                Paragraph(consumo.item_ata_consumido.unidade_medida or '-', styles['TableCell']),
                Paragraph(_format_qty_pdf(consumo.quantidade_consumida), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(consumo.valor_unitario_no_consumo), styles['TableCellRight']),
                Paragraph(_format_br_currency_pdf(consumo.valor_total_consumido_item), styles['TableCellRight']),
            ])
        t = Table(data, colWidths=[3.2*inch, 0.5*inch, 1*inch, 1.1*inch, 1.1*inch], repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        story.append(t)

    if empenho.comments.count() > 0:
        story.append(Paragraph("Comentários", styles['Subtitulo']))
        for comment in empenho.comments:
            story.append(Paragraph(f"{comment.author.username} em {comment.timestamp.strftime('%d/%m/%Y %H:%M')}:", styles['CommentUser']))
            story.append(Paragraph(comment.content.replace('\n', '<br/>'), styles['CommentContent']))
            story.append(Spacer(1, 0.1*inch))

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()
    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=empenho_{empenho.numero_empenho.replace("/", "-")}.pdf'
    return response

def gerar_pdf_consumo_por_unidade(unidade, dados_consumo, data_inicio_filtro, data_fim_filtro):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.75*inch, bottomMargin=1*inch) 
    
    styles = get_default_styles()
    story = []

    titulo_txt = f"Relatório de Consumo - Unidade: {unidade.nome_unidade}"
    story.append(Paragraph(titulo_txt, styles['TituloRelatorio']))

    periodo_str = "Todo o período"
    if data_inicio_filtro and data_fim_filtro:
        periodo_str = f"Período: {data_inicio_filtro.strftime('%d/%m/%Y')} a {data_fim_filtro.strftime('%d/%m/%Y')}"
    elif data_inicio_filtro:
        periodo_str = f"Período: A partir de {data_inicio_filtro.strftime('%d/%m/%Y')}"
    elif data_fim_filtro:
        periodo_str = f"Período: Até {data_fim_filtro.strftime('%d/%m/%Y')}"
    
    story.append(Paragraph(periodo_str, styles['InfoGeral']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))
    
    header_content = ["Item Consumido", "Tipo", "Un.", "Ata Origem", "Doc. Origem", "Data Doc.", "Qtd. Cons.", "Valor Total"]
    table_data = [[Paragraph(text, styles['TableHeader']) for text in header_content]]
    
    valor_total_geral_consumido = 0.0

    for consumo in dados_consumo:
        table_data.append([
            Paragraph(consumo.get('item_descricao', '-'), styles['TableCell']),
            Paragraph(str(consumo.get('item_tipo', '-')), styles['TableCell']),
            Paragraph(str(consumo.get('item_unidade', '-')), styles['TableCell']),
            Paragraph(str(consumo.get('ata_origem', '-')), styles['TableCell']),
            Paragraph(str(consumo.get('documento_origem', '-')), styles['TableCell']),
            Paragraph(str(consumo.get('data_documento', '-')), styles['TableCell']),
            Paragraph(_format_qty_pdf(consumo.get('quantidade_consumida', 0)), styles['TableCellRight']),
            Paragraph(_format_br_currency_pdf(consumo.get('valor_total_consumido', 0.0)), styles['TableCellRight'])
        ])
        valor_total_geral_consumido += consumo.get('valor_total_consumido', 0.0)

    consumo_table = Table(table_data, colWidths=[2.4*inch, 0.9*inch, 0.4*inch, 1.0*inch, 1.4*inch, 0.9*inch, 0.8*inch, 1.0*inch], repeatRows=1)
    consumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), 
    ]))
    story.append(consumo_table)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Valor Total Geral Consumido: {_format_br_currency_pdf(valor_total_geral_consumido)}", styles['Normal']))

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
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
    styles = get_default_styles()
    story = []

    story.append(Paragraph("Relatório de Consumo por Item Específico", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))
    story.append(Paragraph(f"<b>Item:</b> {item_selecionado.descricao_item}", styles['InfoGeral']))
    
    periodo_str = "Todo o período"
    if data_inicio_filtro and data_fim_filtro:
        periodo_str = f"Consumo de {data_inicio_filtro.strftime('%d/%m/%Y')} a {data_fim_filtro.strftime('%d/%m/%Y')}"
    elif data_inicio_filtro:
        periodo_str = f"Consumo a partir de {data_inicio_filtro.strftime('%d/%m/%Y')}"
    elif data_fim_filtro:
        periodo_str = f"Consumo até {data_fim_filtro.strftime('%d/%m/%Y')}"
    story.append(Paragraph(f"<b>Período Analisado:</b> {periodo_str}", styles['InfoGeral']))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Detalhamento do Consumo por Unidade de Saúde:", styles['Subtitulo']))
    
    header_content_unidade = ["Unidade de Saúde", "Qtd. Consumida", "Valor Total Consumido"]
    table_data_unidade = [[Paragraph(text, styles['TableHeader']) for text in header_content_unidade]]

    for dados_unidade in dados_consumo_agregado_por_unidade:
        table_data_unidade.append([
            Paragraph(dados_unidade.get('nome_unidade', '-'), styles['TableCell']),
            Paragraph(_format_qty_pdf(dados_unidade.get('total_qtd', 0)), styles['TableCellRight']),
            Paragraph(_format_br_currency_pdf(dados_unidade.get('total_valor', 0.0)), styles['TableCellRight'])
        ])
    
    consumo_unidade_table = Table(table_data_unidade, colWidths=[3.5*inch, 1.5*inch, 2.0*inch], repeatRows=1)
    consumo_unidade_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(consumo_unidade_table)

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    nome_arquivo_item = "".join(c if c.isalnum() else "_" for c in item_selecionado.descricao_item[:30])
    response.headers['Content-Disposition'] = f'inline; filename=rel_consumo_item_{nome_arquivo_item.lower()}.pdf'
    return response

def gerar_pdf_contratos_vigentes_unidade(unidade, contratos, contratinhos, empenhos):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.75*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph(f"Relatório de Documentos Vigentes", styles['TituloRelatorio']))
    story.append(Paragraph(f"<b>Unidade de Saúde:</b> {unidade.nome_unidade}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'), 
    ])

    if contratos:
        story.append(Paragraph("Contratos Clássicos Vigentes", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Nº Contrato", "Objeto", "Fornecedor", "Fim da Vigência"]]]
        for c in contratos:
            data.append([
                Paragraph(c.numero_contrato, styles['TableCell']),
                Paragraph(c.objeto, styles['TableCell']),
                Paragraph(c.fornecedor or '-', styles['TableCell']),
                Paragraph(c.data_fim_vigencia.strftime('%d/%m/%Y') if c.data_fim_vigencia else '-', styles['TableCell']),
            ])
        t = Table(data, colWidths=[1.5*inch, 5.5*inch, 2*inch, 1*inch], repeatRows=1)
        t.setStyle(table_style)
        story.append(t)

    if contratinhos:
        story.append(Paragraph("Contratinhos Vigentes", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Nº Contratinho", "Objeto", "Ata Vinculada", "Fim da Vigência"]]]
        for c in contratinhos:
            data.append([
                Paragraph(c.numero_contratinho, styles['TableCell']),
                Paragraph(c.objeto or '-', styles['TableCell']),
                Paragraph(f"{c.ata_vinculada.numero_ata}/{c.ata_vinculada.ano}" if c.ata_vinculada else '-', styles['TableCell']),
                Paragraph(c.data_fim_vigencia.strftime('%d/%m/%Y') if c.data_fim_vigencia else '-', styles['TableCell']),
            ])
        t = Table(data, colWidths=[1.5*inch, 5.5*inch, 2*inch, 1*inch], repeatRows=1)
        t.setStyle(table_style)
        story.append(t)

    if empenhos:
        story.append(Paragraph("Empenhos Vinculados à Unidade", styles['Subtitulo']))
        data = [[Paragraph(h, styles['TableHeader']) for h in ["Nº Empenho", "Descrição", "Ata Vinculada", "Data de Emissão"]]]
        for e in empenhos:
            data.append([
                Paragraph(e.numero_empenho, styles['TableCell']),
                Paragraph(e.descricao_simples or '-', styles['TableCell']),
                Paragraph(f"{e.ata_vinculada.numero_ata}/{e.ata_vinculada.ano}" if e.ata_vinculada else '-', styles['TableCell']),
                Paragraph(e.data_emissao.strftime('%d/%m/%Y') if e.data_emissao else '-', styles['TableCell']),
            ])
        t = Table(data, colWidths=[1.5*inch, 5.5*inch, 2*inch, 1*inch], repeatRows=1)
        t.setStyle(table_style)
        story.append(t)

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    nome_arquivo = f"rel_vigentes_{unidade.nome_unidade.replace(' ', '_').lower()}.pdf"
    response.headers['Content-Disposition'] = f'inline; filename={nome_arquivo}'
    return response
    
def gerar_pdf_potencial_solicitacao(unidade, cotas_disponiveis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.75*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph(f"Relatório de Potencial de Solicitação", styles['TituloRelatorio']))
    story.append(Paragraph(f"<b>Unidade de Saúde:</b> {unidade.nome_unidade}", styles['InfoGeral']))
    story.append(Paragraph(f"<b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))

    header = ["Ata de Origem", "Validade da Ata", "Item", "Un. Medida", "Cota Total da Unidade", "Saldo Disponível p/ Solicitar"]
    table_data = [[Paragraph(h, styles['TableHeader']) for h in header]]
    
    for cota in cotas_disponiveis:
        saldo_cota = cota.quantidade_prevista - cota.quantidade_consumida
        data_validade_ata = cota.item_ata.ata_mae.data_validade
        data_validade_str = data_validade_ata.strftime('%d/%m/%Y') if data_validade_ata else '-'

        table_data.append([
            Paragraph(f"{cota.item_ata.ata_mae.numero_ata}/{cota.item_ata.ata_mae.ano}", styles['TableCell']),
            Paragraph(data_validade_str, styles['TableCell']),
            Paragraph(cota.item_ata.descricao_item, styles['TableCell']),
            Paragraph(cota.item_ata.unidade_medida or '-', styles['TableCell']),
            Paragraph(_format_qty_pdf(cota.quantidade_prevista), styles['TableCellRight']),
            Paragraph(f"<b>{_format_qty_pdf(saldo_cota)}</b>", styles['TableCellRight']),
        ])

    t = Table(table_data, colWidths=[1.2*inch, 1*inch, 4.3*inch, 0.8*inch, 1.6*inch, 1.6*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    nome_arquivo = f"rel_potencial_{unidade.nome_unidade.replace(' ', '_').lower()}.pdf"
    response.headers['Content-Disposition'] = f'inline; filename={nome_arquivo}'
    return response

# --- NOVA FUNÇÃO PARA RELATÓRIO DE PROCESSOS ---
def gerar_pdf_lista_processos(todos_os_processos):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.75*inch, bottomMargin=1*inch)
    styles = get_default_styles()
    story = []

    story.append(Paragraph("Relatório - Listagem de Processos Administrativos", styles['TituloRelatorio']))
    story.append(Paragraph(f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['InfoData']))

    table_data = [
        [
            Paragraph("Nº Processo/Ano", styles['TableHeader']),
            Paragraph("Descrição/Objeto", styles['TableHeader']),
            Paragraph("Docs Vinculados", styles['TableHeader'])
        ]
    ]

    for processo in todos_os_processos:
        total_docs = (processo.atas.count() + 
                      processo.contratos.count() + 
                      processo.contratinhos.count() + 
                      processo.empenhos.count())
                      
        table_data.append([
            Paragraph(f"{processo.numero_processo}/{processo.ano}", styles['TableCell']),
            Paragraph(processo.descricao if processo.descricao else '-', styles['TableCell']),
            Paragraph(str(total_docs), styles['TableCellRight'])
        ])
    
    processo_table = Table(table_data, colWidths=[2*inch, 7*inch, 1*inch], repeatRows=1)
    processo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(processo_table)

    doc.build(story, onFirstPage=_my_page_template, onLaterPages=_my_page_template)
    pdf_value = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_value)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=relatorio_lista_processos.pdf'
    return response

# Fim do arquivo completo: reports.py
