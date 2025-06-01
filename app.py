import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.exc import IntegrityError
from wtforms.validators import ValidationError # Importação correta
from sqlalchemy import func
import locale 

from models import (
    db, Ata, Contrato, Contratinho, Empenho, ItemAta, UnidadeSaude,
    ConsumoItemContratinho, ConsumoItemEmpenho, ItemContrato
)
from forms import (
    AtaForm, ContratoForm, ContratinhoForm, EmpenhoForm, ItemAtaForm, UnidadeSaudeForm,
    AdicionarItensLoteAtaForm, RelatorioConsumoUnidadeForm, RelatorioConsumoPorItemForm
)
import reports

app = Flask(__name__)

app.config['SECRET_KEY'] = 'sua-chave-secreta-super-segura-e-diferente-aqui-local!'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERCENTUAL_SALDO_BAIXO'] = 0.20
app.config['DIAS_ALERTA_PRAZO'] = 30 

DATABASE_URL_ENV = os.environ.get('DATABASE_URL')
if DATABASE_URL_ENV:
    uri = DATABASE_URL_ENV
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    if '?sslmode=' not in uri and not uri.endswith('?sslmode=require'):
        uri += '?sslmode=require'
    elif '?sslmode=' in uri and not uri.endswith('sslmode=require'):
        uri = uri.split('?sslmode=')[0] + '?sslmode=require'
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'saude_contratos.db')

# --- FILTROS JINJA2 CUSTOMIZADOS ---
@app.template_filter('br_currency')
def format_br_currency_filter(value):
    if value is None:
        return "R$ 0,00" 
    try:
        num_value = float(value)
        current_locale = locale.getlocale(locale.LC_MONETARY) 
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_ALL, 'ptb') 
                except locale.Error:
                    formatted_fallback = f"{num_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    if current_locale != (None, None) and current_locale[0] is not None:
                        try: locale.setlocale(locale.LC_ALL, current_locale)
                        except: pass 
                    return f"R$ {formatted_fallback}"
        
        formatted_value = locale.currency(num_value, symbol=True, grouping=True, international=False)
        if current_locale != (None, None) and current_locale[0] is not None:
            try: locale.setlocale(locale.LC_ALL, current_locale)
            except: pass
        return formatted_value
    except (ValueError, TypeError):
        return value 

@app.template_filter('format_quantity')
def format_quantity_filter(value):
    if value is None:
        return "-"
    try:
        num_value = float(value)
        if num_value == int(num_value):
            return int(num_value)
        else:
            return f"{num_value:.2f}".replace('.', ',')
    except (ValueError, TypeError):
        return value

@app.context_processor
def inject_current_year():
    return {'ano_atual': datetime.now(timezone.utc).year}

db.init_app(app)
migrate = Migrate(app, db)

# --- ROTA PARA O DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    # ... (código do dashboard como na versão anterior) ...
    totais = {
        'atas': Ata.query.count(),
        'contratos': Contrato.query.count(),
        'contratinhos': Contratinho.query.count(),
        'empenhos': Empenho.query.count(),
        'itens_ata': ItemAta.query.count(),
        'unidades_saude': UnidadeSaude.query.count()
    }
    
    percentual_limite = app.config['PERCENTUAL_SALDO_BAIXO']
    itens_saldo_baixo = ItemAta.query.filter(
        ItemAta.quantidade_registrada > 0,
        (ItemAta.saldo_disponivel / ItemAta.quantidade_registrada) <= percentual_limite
    ).order_by(ItemAta.saldo_disponivel).all()

    dias_prazo_config_default = app.config.get('DIAS_ALERTA_PRAZO', 30) 
    try:
        dias_prazo_atual = request.args.get('dias_prazo', default=dias_prazo_config_default, type=int)
        if not (1 <= dias_prazo_atual <= 365): 
            dias_prazo_atual = dias_prazo_config_default
            if request.args.get('dias_prazo') is not None: 
                 flash('Prazo para alerta inválido (deve ser entre 1 e 365 dias). Usando o valor padrão.', 'warning')
    except (ValueError, TypeError): 
        dias_prazo_atual = dias_prazo_config_default
        if request.args.get('dias_prazo') is not None:
            flash('Valor para prazo de alerta inválido. Usando o valor padrão.', 'warning')

    hoje_obj = datetime.now(timezone.utc)
    data_alerta_prazo_obj = hoje_obj + timedelta(days=dias_prazo_atual)

    atas_vencendo = Ata.query.filter(Ata.data_validade != None, Ata.data_validade <= data_alerta_prazo_obj.date()).order_by(Ata.data_validade).all()
    contratos_vencendo = Contrato.query.filter(Contrato.data_fim_vigencia != None, Contrato.data_fim_vigencia <= data_alerta_prazo_obj.date()).order_by(Contrato.data_fim_vigencia).all()
    contratinhos_vencendo = Contratinho.query.filter(Contratinho.data_fim_vigencia != None, Contratinho.data_fim_vigencia <= data_alerta_prazo_obj.date()).order_by(Contratinho.data_fim_vigencia).all()
    
    return render_template('dashboard.html',
                           titulo_pagina="Dashboard",
                           totais=totais,
                           itens_saldo_baixo=itens_saldo_baixo,
                           percentual_saldo_baixo=int(percentual_limite*100),
                           atas_vencendo=atas_vencendo,
                           contratos_vencendo=contratos_vencendo,
                           contratinhos_vencendo=contratinhos_vencendo,
                           dias_alerta_prazo_atual=dias_prazo_atual, 
                           hoje_datetime=hoje_obj)


# --- ROTAS PARA ATAS ---
# ... (rotas de Ata e ItemAta como na versão anterior) ...
@app.route('/')
@app.route('/atas')
def index():
    todas_as_atas = Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()).all()
    return render_template('listar_atas.html',
                           titulo_pagina="Atas Registradas",
                           lista_de_atas=todas_as_atas)

@app.route('/ata/nova', methods=['GET', 'POST'])
def criar_ata():
    form = AtaForm()
    if form.validate_on_submit():
        try:
            nova_ata_db = Ata(numero_ata=form.numero_ata.data, ano=form.ano.data,
                              descricao=form.descricao.data, data_assinatura=form.data_assinatura.data,
                              data_validade=form.data_validade.data)
            db.session.add(nova_ata_db)
            db.session.commit()
            flash('Ata criada com sucesso! Agora adicione os itens a esta ata.', 'success')
            return redirect(url_for('adicionar_itens_lote_ata', ata_id=nova_ata_db.id))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe uma ata com este número. Verifique os dados.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar ata: {str(e)}', 'danger')
    return render_template('criar_ata.html', titulo_pagina="Criar Nova Ata", form=form)

@app.route('/ata/editar/<int:ata_id>', methods=['GET', 'POST'])
def editar_ata(ata_id):
    ata_para_editar = Ata.query.get_or_404(ata_id)
    form = AtaForm(obj=ata_para_editar)
    if form.validate_on_submit():
        try:
            form.populate_obj(ata_para_editar)
            db.session.commit()
            flash('Ata atualizada com sucesso!', 'success')
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe uma ata com este número. Verifique os dados.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar ata: {str(e)}', 'danger')
    return render_template('editar_ata.html', titulo_pagina="Editar Ata", form=form, ata_id=ata_id)

@app.route('/ata/excluir/<int:ata_id>', methods=['GET'])
def excluir_ata(ata_id):
    ata_para_excluir = Ata.query.get_or_404(ata_id)
    try:
        itens_em_uso = False
        for item_ata in ata_para_excluir.itens_ata:
            if ConsumoItemContratinho.query.filter_by(item_ata_id=item_ata.id).first() or \
               ConsumoItemEmpenho.query.filter_by(item_ata_id=item_ata.id).first():
                itens_em_uso = True
                break
        
        if itens_em_uso:
            flash('Não é possível excluir a ata. Existem itens desta ata que já foram consumidos em Contratinhos ou Empenhos.', 'danger')
            return redirect(url_for('index'))

        for item_ata in list(ata_para_excluir.itens_ata): 
            db.session.delete(item_ata)
        
        db.session.delete(ata_para_excluir)
        db.session.commit()
        flash('Ata e todos os seus itens foram excluídos com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir ata: {str(e)}. Verifique as dependências.', 'danger')
        app.logger.error(f"Erro ao excluir ata {ata_id}: {e}", exc_info=True)
    return redirect(url_for('index'))

@app.route('/ata/<int:ata_id>/itens')
def listar_itens_da_ata(ata_id):
    ata = Ata.query.get_or_404(ata_id)
    tipo_item_display_map = dict(ItemAta.TIPO_ITEM_CHOICES)
    itens = ItemAta.query.filter_by(ata_id=ata.id).order_by(ItemAta.descricao_item).all()
    return render_template('listar_itens_ata.html',
                           titulo_pagina=f"Itens da Ata {ata.numero_ata}/{ata.ano}",
                           ata=ata,
                           itens_da_ata=itens,
                           tipo_item_display_map=tipo_item_display_map)

@app.route('/itens_da_ata_json/<int:ata_id>')
def itens_da_ata_json(ata_id):
    try:
        ata_id_int = int(ata_id)
    except ValueError:
        return jsonify({'error': 'ID da Ata inválido'}), 400

    ata_obj = db.session.get(Ata, ata_id_int)
    if not ata_obj:
        return jsonify({'error': 'Ata não encontrada'}), 404

    itens_query = ItemAta.query.filter_by(ata_id=ata_id_int).filter(ItemAta.saldo_disponivel > 0).order_by(ItemAta.descricao_item).all() 
    
    payload = {
        'ata_descricao': ata_obj.descricao if ata_obj.descricao else f'Ata {ata_obj.numero_ata}/{ata_obj.ano}',
        'itens': []
    }

    itens_list = []
    if itens_query:
        itens_list = [
            {'id': item.id, 'text': f"{item.descricao_item} (Saldo: {item.saldo_disponivel:.2f} {item.unidade_medida or ''}, VU: R${item.valor_unitario_registrado:.2f})"}
            for item in itens_query 
        ]
        payload['itens'] = [{'id': '', 'text': '--- Selecione um Item ---'}] + itens_list
    else:
        if ItemAta.query.filter_by(ata_id=ata_id_int).first():
             payload['itens'] = [{'id': '', 'text': 'Todos os itens desta Ata estão com saldo zero'}]
        else:
             payload['itens'] = [{'id': '', 'text': 'Nenhum item cadastrado para esta Ata'}]
        
    return jsonify(payload)

@app.route('/ata/<int:ata_id>/item/novo', methods=['GET', 'POST'])
def criar_item_ata(ata_id):
    ata = Ata.query.get_or_404(ata_id)
    form = ItemAtaForm() 
    if form.validate_on_submit():
        try:
            novo_item = ItemAta(ata_id=ata.id) 
            form.populate_obj(novo_item) 
            novo_item.saldo_disponivel = novo_item.quantidade_registrada 
            
            db.session.add(novo_item)
            db.session.commit()
            flash('Item adicionado à ata com sucesso!', 'success')
            return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar item à ata: {str(e)}', 'danger')
            app.logger.error(f"Erro ao criar item para ata {ata_id}: {e}", exc_info=True)
    return render_template('criar_item_ata.html',
                           titulo_pagina=f"Adicionar Item à Ata {ata.numero_ata}/{ata.ano}",
                           form=form,
                           ata_id_ref=ata.id,
                           ata_numero=f"{ata.numero_ata}/{ata.ano}")

@app.route('/ata/<int:ata_id>/adicionar_itens_lote', methods=['GET', 'POST'])
def adicionar_itens_lote_ata(ata_id):
    ata = Ata.query.get_or_404(ata_id)
    form = AdicionarItensLoteAtaForm(request.form) 

    if form.validate_on_submit():
        try:
            novos_itens_criados = 0
            for item_data in form.itens_ata.data:
                if item_data.get('descricao_item') and item_data.get('quantidade_registrada') is not None:
                    novo_item = ItemAta(
                        ata_id=ata.id,
                        descricao_item=item_data['descricao_item'],
                        tipo_item=item_data['tipo_item'],
                        unidade_medida=item_data.get('unidade_medida'),
                        quantidade_registrada=item_data['quantidade_registrada'],
                        valor_unitario_registrado=item_data.get('valor_unitario_registrado'),
                        lote=item_data.get('lote')
                    )
                    novo_item.saldo_disponivel = novo_item.quantidade_registrada
                    db.session.add(novo_item)
                    novos_itens_criados += 1
            
            if novos_itens_criados > 0:
                db.session.commit()
                flash(f'{novos_itens_criados} item(ns) adicionado(s) à ata com sucesso!', 'success')
            else:
                flash('Nenhum item foi adicionado. Preencha os dados dos itens, incluindo a quantidade registrada.', 'info')
            return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))
        except ValidationError as ve: 
            flash(f'Erro de validação ao adicionar itens: {str(ve)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar itens em lote à ata: {str(e)}', 'danger')
            app.logger.error(f"Erro ao adicionar itens em lote à ata {ata_id}: {e}", exc_info=True)
            
    return render_template('adicionar_itens_lote_ata.html',
                           titulo_pagina=f"Adicionar Múltiplos Itens à Ata {ata.numero_ata}/{ata.ano}",
                           form=form,
                           ata=ata)

@app.route('/ata/<int:ata_id>/item/<int:item_id>/editar', methods=['GET', 'POST'])
def editar_item_ata(ata_id, item_id):
    ata = Ata.query.get_or_404(ata_id)
    item_para_editar = ItemAta.query.get_or_404(item_id)
    if item_para_editar.ata_id != ata.id:
        flash('Item não pertence à ata especificada.', 'danger')
        return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))

    saldo_antes_edicao = item_para_editar.saldo_disponivel
    qtd_registrada_antes_edicao = item_para_editar.quantidade_registrada
    form = ItemAtaForm(obj=item_para_editar) 

    if form.validate_on_submit():
        try:
            qtd_consumida_total_calculada = qtd_registrada_antes_edicao - saldo_antes_edicao
            
            form.populate_obj(item_para_editar) 
            
            novo_saldo = item_para_editar.quantidade_registrada - qtd_consumida_total_calculada
            if novo_saldo < 0:
                item_para_editar.quantidade_registrada = qtd_registrada_antes_edicao 
                flash('A nova quantidade registrada é menor que a quantidade já consumida. Ajuste os consumos ou aumente a quantidade.', 'danger')
            else:
                item_para_editar.saldo_disponivel = novo_saldo
                db.session.commit()
                flash('Item da ata atualizado com sucesso!', 'success')
                return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar item da ata: {str(e)}', 'danger')
            app.logger.error(f"Erro ao editar item da ata {item_id}: {e}", exc_info=True)
            
    return render_template('editar_item_ata.html',
                           titulo_pagina=f"Editar Item da Ata {item_para_editar.descricao_item[:30]}...",
                           form=form,
                           ata_id_ref=ata.id,
                           ata_numero=f"{ata.numero_ata}/{ata.ano}",
                           item_id=item_id,
                           saldo_atual_item=item_para_editar.saldo_disponivel)

@app.route('/ata/<int:ata_id>/item/<int:item_id>/excluir', methods=['GET'])
def excluir_item_ata(ata_id, item_id):
    ata = Ata.query.get_or_404(ata_id)
    item_para_excluir = ItemAta.query.get_or_404(item_id)
    if item_para_excluir.ata_id != ata.id:
        flash('Item não pertence à ata especificada.', 'danger')
        return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))

    if ConsumoItemContratinho.query.filter_by(item_ata_id=item_id).first() or \
       ConsumoItemEmpenho.query.filter_by(item_ata_id=item_id).first():
        flash('Este item não pode ser excluído pois já foi referenciado em Contratinhos ou Empenhos. Remova as referências primeiro.', 'danger')
        return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))
        
    try:
        db.session.delete(item_para_excluir)
        db.session.commit()
        flash('Item da ata excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir item da ata: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir item da ata {item_id}: {e}", exc_info=True)
    return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))

# --- LÓGICA AUXILIAR PARA PROCESSAR ITENS LIVRES (para Contratos Clássicos) ---
def _processar_itens_livres_contrato(form_itens_data, contrato_pai_obj):
    novos_itens_contratados_db = []
    valor_total_dos_itens_calculado = 0.0

    for item_data in form_itens_data:
        descricao = item_data.get('descricao')
        unidade_medida = item_data.get('unidade_medida')
        
        quantidade = 0.0
        valor_unitario = 0.0
        
        # Os campos 'quantidade' e 'valor_unitario' já devem vir como float do formulário
        # devido ao FloatField. A validação DataRequired (se aplicada no subform) garante que eles não são None.
        try:
            raw_quantidade = item_data.get('quantidade')
            if raw_quantidade is not None: # FloatField pode retornar None se entrada inválida e opcional
                quantidade = float(raw_quantidade)
            
            raw_valor_unitario = item_data.get('valor_unitario')
            if raw_valor_unitario is not None:
                valor_unitario = float(raw_valor_unitario)

        except (ValueError, TypeError):
            # Se um valor não puder ser convertido, e o validador do form não pegou (ex: opcional e string vazia),
            # continuará como 0.0. Se a validação do form (DataRequired) estiver ativa, não deve chegar aqui com None.
            app.logger.warning(f"Não foi possível converter quantidade ou valor unitário para float: {item_data}")
            continue # Pula este item se houver erro de conversão, ou se os dados são inválidos

        if descricao and descricao.strip() and quantidade > 0: 
            valor_total_deste_item = quantidade * valor_unitario
            valor_total_dos_itens_calculado += valor_total_deste_item
            
            novo_item_obj = ItemContrato(
                contrato_id=contrato_pai_obj.id,
                descricao=descricao,
                unidade_medida=unidade_medida,
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total_item=valor_total_deste_item
            )
            db.session.add(novo_item_obj)
            novos_itens_contratados_db.append(novo_item_obj)
    
    return novos_itens_contratados_db, valor_total_dos_itens_calculado


# --- ROTAS PARA CONTRATOS ---
@app.route('/contratos')
def listar_contratos():
    todos_os_contratos = Contrato.query.order_by(Contrato.data_assinatura_contrato.desc(), Contrato.numero_contrato.desc()).all()
    return render_template('listar_contratos.html',
                           titulo_pagina="Lista de Contratos",
                           lista_de_contratos=todos_os_contratos)

@app.route('/contrato/visualizar/<int:contrato_id>') 
def visualizar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    return render_template('visualizar_contrato.html',
                           titulo_pagina=f"Detalhes do Contrato {contrato.numero_contrato}",
                           contrato=contrato)

@app.route('/contrato/novo', methods=['GET', 'POST'])
def criar_contrato():
    form = ContratoForm(request.form)
    if form.validate_on_submit():
        try:
            novo_contrato_db = Contrato(
                numero_contrato=form.numero_contrato.data,
                objeto=form.objeto.data,
                valor_global_contrato=form.valor_global_contrato.data,
                fornecedor=form.fornecedor.data,
                data_assinatura_contrato=form.data_assinatura_contrato.data,
                data_inicio_vigencia=form.data_inicio_vigencia.data,
                data_fim_vigencia=form.data_fim_vigencia.data
            )
            db.session.add(novo_contrato_db)
            db.session.flush() 

            itens_processados, valor_calculado_dos_itens_contratados = _processar_itens_livres_contrato(
                form.itens_contratados.data, novo_contrato_db
            )
            novo_contrato_db.valor_total_itens = valor_calculado_dos_itens_contratados
            
            db.session.commit()
            flash('Contrato criado com sucesso!', 'success')
            return redirect(url_for('listar_contratos'))
        except ValueError as ve:
            db.session.rollback()
            flash(str(ve), 'danger')
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um contrato com este número.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar contrato: {str(e)}', 'danger')
            app.logger.error(f"Erro ao criar contrato: {e}", exc_info=True)

    return render_template('criar_contrato.html', titulo_pagina="Criar Novo Contrato", form=form)

@app.route('/contrato/editar/<int:contrato_id>', methods=['GET', 'POST'])
def editar_contrato(contrato_id):
    contrato_para_editar = Contrato.query.get_or_404(contrato_id)
    
    if request.method == 'POST':
        form = ContratoForm(request.form)
    else:
        form = ContratoForm(obj=contrato_para_editar)
        while len(form.itens_contratados.entries) > 0 : form.itens_contratados.pop_entry()
        if contrato_para_editar.itens_do_contrato:
            for item_existente in contrato_para_editar.itens_do_contrato:
                form.itens_contratados.append_entry(data={
                    'descricao': item_existente.descricao,
                    'unidade_medida': item_existente.unidade_medida,
                    'quantidade': item_existente.quantidade,
                    'valor_unitario': item_existente.valor_unitario
                })

    if form.validate_on_submit():
        try:
            for item_antigo in list(contrato_para_editar.itens_do_contrato):
                 db.session.delete(item_antigo)
            db.session.flush()

            contrato_para_editar.numero_contrato = form.numero_contrato.data
            contrato_para_editar.objeto = form.objeto.data
            contrato_para_editar.valor_global_contrato = form.valor_global_contrato.data
            contrato_para_editar.fornecedor = form.fornecedor.data
            contrato_para_editar.data_assinatura_contrato = form.data_assinatura_contrato.data
            contrato_para_editar.data_inicio_vigencia = form.data_inicio_vigencia.data
            contrato_para_editar.data_fim_vigencia = form.data_fim_vigencia.data
            
            itens_processados, novo_valor_total_dos_itens = _processar_itens_livres_contrato(
                form.itens_contratados.data, contrato_para_editar
            )
            contrato_para_editar.valor_total_itens = novo_valor_total_dos_itens
            
            db.session.commit()
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('listar_contratos'))
        except ValueError as ve:
            db.session.rollback()
            flash(str(ve), 'danger')
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um contrato com este número (se estiver alterando).', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar contrato: {str(e)}', 'danger')
            app.logger.error(f"Erro ao editar contrato {contrato_id}: {e}", exc_info=True)

    return render_template('editar_contrato.html', titulo_pagina="Editar Contrato", form=form, contrato_id=contrato_id, contrato=contrato_para_editar)

@app.route('/contrato/excluir/<int:contrato_id>', methods=['GET'])
def excluir_contrato(contrato_id):
    contrato_para_excluir = Contrato.query.get_or_404(contrato_id)
    try:
        db.session.delete(contrato_para_excluir)
        db.session.commit()
        flash('Contrato excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contrato: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir contrato {contrato_id}: {e}", exc_info=True)
    return redirect(url_for('listar_contratos'))

# --- ROTAS PARA UNIDADES DE SAÚDE ---
@app.route('/unidades')
def listar_unidades():
    unidades = UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()
    unidade_tipo_map = dict(UnidadeSaude.TIPO_UNIDADE_CHOICES)
    return render_template('listar_unidades.html', 
                           titulo_pagina="Unidades de Saúde", 
                           unidades=unidades,
                           unidade_tipo_map=unidade_tipo_map)

@app.route('/unidade/nova', methods=['GET', 'POST'])
def criar_unidade():
    form = UnidadeSaudeForm()
    if form.validate_on_submit():
        try:
            nova_unidade = UnidadeSaude()
            form.populate_obj(nova_unidade)
            db.session.add(nova_unidade)
            db.session.commit()
            flash('Unidade de Saúde cadastrada com sucesso!', 'success')
            return redirect(url_for('listar_unidades'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe uma Unidade de Saúde com este nome.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar unidade: {str(e)}', 'danger')
    return render_template('criar_unidade.html', titulo_pagina="Cadastrar Unidade de Saúde", form=form)

@app.route('/unidade/editar/<int:unidade_id>', methods=['GET', 'POST'])
def editar_unidade(unidade_id):
    unidade_para_editar = UnidadeSaude.query.get_or_404(unidade_id)
    form = UnidadeSaudeForm(obj=unidade_para_editar)
    if form.validate_on_submit():
        try:
            form.populate_obj(unidade_para_editar)
            db.session.commit()
            flash('Unidade de Saúde atualizada com sucesso!', 'success')
            return redirect(url_for('listar_unidades'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe uma Unidade de Saúde com este nome (se estiver alterando).', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar unidade: {str(e)}', 'danger')
    return render_template('editar_unidade.html', titulo_pagina="Editar Unidade de Saúde", form=form, unidade_id=unidade_id)

@app.route('/unidade/excluir/<int:unidade_id>', methods=['GET']) 
def excluir_unidade(unidade_id):
    unidade_para_excluir = UnidadeSaude.query.get_or_404(unidade_id)
    if unidade_para_excluir.contratinhos_vinculados.first() or unidade_para_excluir.empenhos_vinculados.first():
        flash('Esta Unidade de Saúde não pode ser excluída pois está vinculada a Contratinhos ou Empenhos.', 'danger')
        return redirect(url_for('listar_unidades'))
    try:
        db.session.delete(unidade_para_excluir)
        db.session.commit()
        flash('Unidade de Saúde excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir unidade: {str(e)}', 'danger')
    return redirect(url_for('listar_unidades'))


# --- LÓGICA AUXILIAR PARA PROCESSAR ITENS CONSUMIDOS (Contratinhos e Empenhos) ---
def _processar_itens_consumidos_para_salvar(form_itens_data, objeto_pai, ModeloConsumoItem, ata_id_principal_do_pai):
    novos_consumos_db_list = []
    valor_total_itens_calculado = 0.0

    itens_a_processar = []
    if isinstance(form_itens_data, list):
        itens_a_processar = form_itens_data
    elif isinstance(form_itens_data, dict) and form_itens_data.get('item_ata_id'): 
        itens_a_processar = [form_itens_data]

    for item_data in itens_a_processar:
        item_id_str = item_data.get('item_ata_id')
        item_id = None
        if item_id_str is not None and str(item_id_str).strip() != '':
            try:
                item_id = int(item_id_str)
            except ValueError:
                raise ValueError(f"ID do item '{item_id_str}' é inválido.")

        quantidade_a_consumir_str = item_data.get('quantidade_consumida', '0.0')
        quantidade_a_consumir = 0.0
        if quantidade_a_consumir_str is not None:
             try:
                quantidade_a_consumir = float(str(quantidade_a_consumir_str)) 
             except (ValueError, TypeError):
                raise ValueError(f"Quantidade consumida '{quantidade_a_consumir_str}' é inválida.")

        if item_id and quantidade_a_consumir > 0:
            item_ata = db.session.get(ItemAta, item_id) 
            if not item_ata:
                raise ValueError(f"Item ID {item_id} não encontrado no banco de dados.")
            
            id_ata_pai_int = None
            try:
                id_ata_pai_int = int(ata_id_principal_do_pai)
            except (ValueError, TypeError):
                 raise ValueError(f"ID da Ata Principal '{ata_id_principal_do_pai}' é inválido.")

            if item_ata.ata_id != id_ata_pai_int:
                raise ValueError(f"Item '{item_ata.descricao_item}' (ID: {item_id}) não pertence à Ata ID {id_ata_pai_int} selecionada.")
            
            if item_ata.saldo_disponivel < quantidade_a_consumir:
                raise ValueError(f"Saldo insuficiente para o item '{item_ata.descricao_item}'. Disponível: {item_ata.saldo_disponivel:.2f}, Solicitado: {quantidade_a_consumir:.2f}.")
            
            item_ata.saldo_disponivel -= quantidade_a_consumir
            
            valor_unit = item_ata.valor_unitario_registrado if item_ata.valor_unitario_registrado is not None else 0.0
            valor_item_consumido_neste_lancamento = quantidade_a_consumir * valor_unit
            valor_total_itens_calculado += valor_item_consumido_neste_lancamento
            
            consumo_kwargs = {
                'item_ata_id': item_ata.id,
                'quantidade_consumida': quantidade_a_consumir,
                'valor_unitario_no_consumo': valor_unit,
                'valor_total_consumido_item': valor_item_consumido_neste_lancamento
            }
            
            if isinstance(objeto_pai, Contratinho):
                consumo_kwargs['contratinho_id'] = objeto_pai.id
            elif isinstance(objeto_pai, Empenho):
                consumo_kwargs['empenho_id'] = objeto_pai.id
            
            novo_consumo_obj = ModeloConsumoItem(**consumo_kwargs)
            db.session.add(novo_consumo_obj) 
            novos_consumos_db_list.append(novo_consumo_obj)
    
    return novos_consumos_db_list, valor_total_itens_calculado

def _helper_popula_choices_itens_subform(form_principal, subform_fieldlist, ata_id_para_filtro):
    item_choices = [('', '--- Selecione uma Ata Principal Primeiro ---')]
    if ata_id_para_filtro is not None:
        try: 
            id_ata_int = int(ata_id_para_filtro)
            itens_query = ItemAta.query.filter_by(ata_id=id_ata_int).filter(ItemAta.saldo_disponivel > 0).order_by(ItemAta.descricao_item).all()
            if itens_query:
                item_choices = [('', '--- Selecione um Item ---')] + \
                               [(item.id, f"{item.descricao_item} (Saldo: {item.saldo_disponivel:.2f} {item.unidade_medida or ''}, VU: R${item.valor_unitario_registrado:.2f})")
                                for item in itens_query]
            else:
                if ItemAta.query.filter_by(ata_id=id_ata_int).first():
                     item_choices = [('', 'Todos os itens desta Ata estão com saldo zero')]
                else:
                     item_choices = [('', 'Nenhum item cadastrado para esta Ata')]
        except (ValueError, TypeError): 
             item_choices = [('', 'ID da Ata inválido para filtro')]
    
    target_field_name = 'item_ata_id'

    for entry_form_field in subform_fieldlist: 
        if hasattr(entry_form_field, 'form') and hasattr(entry_form_field.form, target_field_name):
            getattr(entry_form_field.form, target_field_name).choices = item_choices


# --- ROTAS PARA CONTRATINHOS ---
@app.route('/contratinhos')
def listar_contratinhos():
    todos_os_contratinhos = Contratinho.query.order_by(Contratinho.data_emissao.desc()).all()
    return render_template('listar_contratinhos.html',
                           titulo_pagina="Lista de Contratinhos",
                           lista_de_contratinhos=todos_os_contratinhos)

@app.route('/contratinho/novo', methods=['GET', 'POST'])
def criar_contratinho():
    form = ContratinhoForm(request.form) 
    
    id_ata_para_choices = form.ata_id.data if form.ata_id.data is not None else None
    _helper_popula_choices_itens_subform(form, form.itens_consumidos, id_ata_para_choices)

    if form.validate_on_submit():
        try:
            novo_contratinho = Contratinho(
                numero_contratinho=form.numero_contratinho.data,
                objeto=form.objeto.data,
                favorecido=form.favorecido.data,
                data_emissao=form.data_emissao.data,
                data_fim_vigencia=form.data_fim_vigencia.data,
                ata_id=form.ata_id.data,
                unidade_saude_id=form.unidade_saude_id.data,
                valor_total_manual=form.valor_total_manual.data
            )
            db.session.add(novo_contratinho)
            db.session.flush() 

            consumos_processados, valor_total_calculado_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, novo_contratinho, ConsumoItemContratinho, novo_contratinho.ata_id
            )
            novo_contratinho.valor_total_itens = valor_total_calculado_dos_itens
            
            db.session.commit()
            flash('Contratinho registrado com sucesso!', 'success')
            return redirect(url_for('listar_contratinhos'))
            
        except ValueError as ve:
            db.session.rollback()
            flash(str(ve), 'danger')
        except IntegrityError as ie: 
            db.session.rollback()
            flash(f'Erro de integridade ao salvar Contratinho: {str(ie)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro inesperado ao registrar contratinho: {str(e)}', 'danger')
            app.logger.error(f"Erro ao criar contratinho: {e}", exc_info=True)
            _helper_popula_choices_itens_subform(form, form.itens_consumidos, form.ata_id.data if form.ata_id.data else None)
            
    return render_template('criar_contratinho.html', titulo_pagina="Registrar Novo Contratinho", form=form)

@app.route('/contratinho/visualizar/<int:contratinho_id>')
def visualizar_contratinho(contratinho_id):
    contratinho = Contratinho.query.get_or_404(contratinho_id)
    tipo_item_display_map = dict(ItemAta.TIPO_ITEM_CHOICES) 
    return render_template('visualizar_contratinho.html',
                           titulo_pagina=f"Detalhes do Contratinho {contratinho.numero_contratinho}",
                           contratinho=contratinho,
                           tipo_item_display_map=tipo_item_display_map)

@app.route('/contratinho/editar/<int:contratinho_id>', methods=['GET', 'POST'])
def editar_contratinho(contratinho_id):
    ct_para_editar = Contratinho.query.get_or_404(contratinho_id)
    
    if request.method == 'POST':
        form = ContratinhoForm(request.form)
    else:
        form = ContratinhoForm(obj=ct_para_editar)
        while len(form.itens_consumidos.entries) > 0 : form.itens_consumidos.pop_entry()
        if ct_para_editar.itens_consumidos: 
            for consumo_existente in ct_para_editar.itens_consumidos:
                form.itens_consumidos.append_entry(data={
                    'item_ata_id': consumo_existente.item_ata_id,
                    'quantidade_consumida': consumo_existente.quantidade_consumida
                })
        
        num_entries_needed = form.itens_consumidos.min_entries - len(form.itens_consumidos.entries)
        if num_entries_needed > 0:
            for _ in range(num_entries_needed):
                 form.itens_consumidos.append_entry()

    ata_id_atual_ou_selecionada = form.ata_id.data if form.ata_id.data is not None else ct_para_editar.ata_id
    _helper_popula_choices_itens_subform(form, form.itens_consumidos, ata_id_atual_ou_selecionada)

    if form.validate_on_submit():
        try:
            for consumo_antigo in ct_para_editar.itens_consumidos:
                item_ata_antigo = db.session.get(ItemAta, consumo_antigo.item_ata_id)
                if item_ata_antigo:
                    item_ata_antigo.saldo_disponivel += consumo_antigo.quantidade_consumida
            
            for consumo_antigo in list(ct_para_editar.itens_consumidos): 
                 db.session.delete(consumo_antigo)
            db.session.flush() 

            ct_para_editar.numero_contratinho = form.numero_contratinho.data
            ct_para_editar.objeto = form.objeto.data
            ct_para_editar.favorecido = form.favorecido.data
            ct_para_editar.data_emissao = form.data_emissao.data
            ct_para_editar.data_fim_vigencia = form.data_fim_vigencia.data
            ct_para_editar.ata_id = form.ata_id.data
            ct_para_editar.unidade_saude_id = form.unidade_saude_id.data
            ct_para_editar.valor_total_manual = form.valor_total_manual.data
            
            id_ata_para_processar_itens = form.ata_id.data if form.ata_id.data else ct_para_editar.ata_id
            consumos_processados, novo_valor_total_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, ct_para_editar, ConsumoItemContratinho, id_ata_para_processar_itens
            )
            ct_para_editar.valor_total_itens = novo_valor_total_dos_itens
            
            db.session.commit()
            flash('Contratinho atualizado com sucesso!', 'success')
            return redirect(url_for('listar_contratinhos'))
            
        except ValueError as ve:
            db.session.rollback()
            flash(str(ve), 'danger')
        except IntegrityError as ie:
            db.session.rollback()
            flash(f'Erro de integridade ao atualizar Contratinho: {str(ie)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar contratinho: {str(e)}', 'danger')
            app.logger.error(f"Erro ao editar contratinho {contratinho_id}: {e}", exc_info=True)
            _helper_popula_choices_itens_subform(form, form.itens_consumidos, ata_id_atual_ou_selecionada) 
            
    return render_template('editar_contratinho.html', titulo_pagina="Editar Contratinho", form=form, contratinho_id=contratinho_id, contratinho=ct_para_editar)

@app.route('/contratinho/excluir/<int:contratinho_id>', methods=['GET'])
def excluir_contratinho(contratinho_id):
    ct_para_excluir = Contratinho.query.get_or_404(contratinho_id)
    try:
        for consumo in ct_para_excluir.itens_consumidos:
            item_afetado = db.session.get(ItemAta, consumo.item_ata_id)
            if item_afetado:
                item_afetado.saldo_disponivel += consumo.quantidade_consumida
        
        db.session.delete(ct_para_excluir)
        db.session.commit()
        flash('Contratinho excluído com sucesso! Saldos dos itens foram restaurados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contratinho: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir contratinho {contratinho_id}: {e}", exc_info=True)
    return redirect(url_for('listar_contratinhos'))

# --- ROTAS PARA EMPENHOS ---
@app.route('/empenhos')
def listar_empenhos():
    todos_os_empenhos = Empenho.query.order_by(Empenho.data_emissao.desc()).all()
    return render_template('listar_empenhos.html',
                           titulo_pagina="Lista de Empenhos",
                           lista_de_empenhos=todos_os_empenhos)

@app.route('/empenho/visualizar/<int:empenho_id>') 
def visualizar_empenho(empenho_id):
    empenho = Empenho.query.get_or_404(empenho_id)
    tipo_item_display_map = dict(ItemAta.TIPO_ITEM_CHOICES)
    return render_template('visualizar_empenho.html',
                           titulo_pagina=f"Detalhes do Empenho {empenho.numero_empenho}",
                           empenho=empenho,
                           tipo_item_display_map=tipo_item_display_map)

@app.route('/empenho/novo', methods=['GET', 'POST'])
def criar_empenho():
    form = EmpenhoForm(request.form)

    id_ata_para_choices = form.ata_id.data if form.ata_id.data is not None else None
    _helper_popula_choices_itens_subform(form, form.itens_consumidos, id_ata_para_choices)

    if form.validate_on_submit():
        try:
            novo_empenho = Empenho(
                numero_empenho=form.numero_empenho.data,
                descricao_simples=form.descricao_simples.data,
                favorecido=form.favorecido.data,
                data_emissao=form.data_emissao.data,
                ata_id=form.ata_id.data,
                unidade_saude_id=form.unidade_saude_id.data,
                valor_total_manual=form.valor_total_manual.data
            )
            db.session.add(novo_empenho)
            db.session.flush()

            consumos_processados, valor_total_calculado_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, novo_empenho, ConsumoItemEmpenho, novo_empenho.ata_id
            )
            novo_empenho.valor_total_itens = valor_total_calculado_dos_itens
            
            db.session.commit()
            flash('Empenho registrado com sucesso!', 'success')
            return redirect(url_for('listar_empenhos'))
        except ValueError as ve:
            db.session.rollback()
            flash(str(ve), 'danger')
        except IntegrityError as ie:
            db.session.rollback()
            flash(f'Erro de integridade ao salvar Empenho: {str(ie)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro inesperado ao registrar empenho: {str(e)}', 'danger')
            app.logger.error(f"Erro ao criar empenho: {e}", exc_info=True)
            _helper_popula_choices_itens_subform(form, form.itens_consumidos, form.ata_id.data if form.ata_id.data else None)

    return render_template('criar_empenho.html', titulo_pagina="Registrar Empenho", form=form)

@app.route('/empenho/editar/<int:empenho_id>', methods=['GET', 'POST'])
def editar_empenho(empenho_id):
    emp_para_editar = Empenho.query.get_or_404(empenho_id)
    
    if request.method == 'POST':
        form = EmpenhoForm(request.form)
    else:
        form = EmpenhoForm(obj=emp_para_editar)
        while len(form.itens_consumidos.entries) > 0: form.itens_consumidos.pop_entry()
        if emp_para_editar.itens_consumidos: 
            for consumo_existente in emp_para_editar.itens_consumidos:
                form.itens_consumidos.append_entry(data={
                    'item_ata_id': consumo_existente.item_ata_id,
                    'quantidade_consumida': consumo_existente.quantidade_consumida
                })
        
        num_entries_needed = form.itens_consumidos.min_entries - len(form.itens_consumidos.entries)
        if num_entries_needed > 0:
            for _ in range(num_entries_needed):
                form.itens_consumidos.append_entry()

    ata_id_atual_ou_selecionada = form.ata_id.data if form.ata_id.data is not None else emp_para_editar.ata_id
    _helper_popula_choices_itens_subform(form, form.itens_consumidos, ata_id_atual_ou_selecionada)
        
    if form.validate_on_submit():
        try:
            for consumo_antigo in emp_para_editar.itens_consumidos:
                item_ata_antigo = db.session.get(ItemAta, consumo_antigo.item_ata_id)
                if item_ata_antigo:
                    item_ata_antigo.saldo_disponivel += consumo_antigo.quantidade_consumida
            
            for consumo_antigo in list(emp_para_editar.itens_consumidos):
                db.session.delete(consumo_antigo)
            db.session.flush()

            emp_para_editar.numero_empenho = form.numero_empenho.data
            emp_para_editar.descricao_simples = form.descricao_simples.data
            emp_para_editar.favorecido = form.favorecido.data
            emp_para_editar.data_emissao = form.data_emissao.data
            emp_para_editar.ata_id = form.ata_id.data
            emp_para_editar.unidade_saude_id = form.unidade_saude_id.data
            emp_para_editar.valor_total_manual = form.valor_total_manual.data

            id_ata_para_processar_itens = form.ata_id.data if form.ata_id.data else emp_para_editar.ata_id
            consumos_processados, novo_valor_total_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, emp_para_editar, ConsumoItemEmpenho, id_ata_para_processar_itens
            )
            emp_para_editar.valor_total_itens = novo_valor_total_dos_itens
            
            db.session.commit()
            flash('Empenho atualizado com sucesso!', 'success')
            return redirect(url_for('listar_empenhos'))
        except ValueError as ve:
            db.session.rollback()
            flash(str(ve), 'danger')
        except IntegrityError as ie:
            db.session.rollback()
            flash(f'Erro de integridade ao atualizar Empenho: {str(ie)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar empenho: {str(e)}', 'danger')
            app.logger.error(f"Erro ao editar empenho {empenho_id}: {e}", exc_info=True)
            _helper_popula_choices_itens_subform(form, form.itens_consumidos, ata_id_atual_ou_selecionada)
                
    return render_template('editar_empenho.html', titulo_pagina="Editar Empenho", form=form, empenho_id=empenho_id, empenho=emp_para_editar)

@app.route('/empenho/excluir/<int:empenho_id>', methods=['GET'])
def excluir_empenho(empenho_id):
    emp_para_excluir = Empenho.query.get_or_404(empenho_id)
    try:
        for consumo in emp_para_excluir.itens_consumidos:
            item_afetado = db.session.get(ItemAta, consumo.item_ata_id)
            if item_afetado:
                item_afetado.saldo_disponivel += consumo.quantidade_consumida
        
        db.session.delete(emp_para_excluir)
        db.session.commit()
        flash('Empenho excluído com sucesso! Saldos dos itens foram restaurados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir empenho: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir empenho {empenho_id}: {e}", exc_info=True)
    return redirect(url_for('listar_empenhos'))

# --- ROTAS PARA RELATÓRIOS PDF ---
@app.route('/relatorio/atas/todas')
def relatorio_lista_atas_pdf():
    todas_as_atas = Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()).all()
    if not todas_as_atas:
        flash('Nenhuma ata encontrada para gerar o relatório.', 'warning')
        return redirect(url_for('index')) 
    return reports.gerar_pdf_lista_atas(todas_as_atas)

@app.route('/relatorio/ata/<int:ata_id>/detalhes')
def relatorio_detalhes_ata_pdf(ata_id):
    ata = Ata.query.get_or_404(ata_id)
    return reports.gerar_pdf_detalhes_ata(ata, ata.itens_ata)

@app.route('/relatorio/consumo_unidade', methods=['GET', 'POST'])
def relatorio_consumo_unidade():
    form = RelatorioConsumoUnidadeForm()
    if form.validate_on_submit():
        unidade_id = form.unidade_saude_id.data
        data_inicio = form.data_inicio.data
        data_fim = form.data_fim.data

        unidade = db.session.get(UnidadeSaude, unidade_id)
        if not unidade:
            flash('Unidade de Saúde não encontrada.', 'danger')
            return redirect(url_for('relatorio_consumo_unidade'))

        query_contratinhos = db.session.query(
            ItemAta.descricao_item, ItemAta.tipo_item, ItemAta.unidade_medida,
            Ata.numero_ata.label('num_ata'), Ata.ano.label('ano_ata'),
            Contratinho.numero_contratinho.label('documento_origem'),
            Contratinho.data_emissao.label('data_documento'),
            ConsumoItemContratinho.quantidade_consumida.label('qtd_consumida_total'),
            ConsumoItemContratinho.valor_total_consumido_item.label('vlr_consumido_total')
        ).join(Contratinho, ConsumoItemContratinho.contratinho_id == Contratinho.id)\
         .join(ItemAta, ConsumoItemContratinho.item_ata_id == ItemAta.id)\
         .join(Ata, ItemAta.ata_id == Ata.id)\
         .filter(Contratinho.unidade_saude_id == unidade_id)

        query_empenhos = db.session.query(
            ItemAta.descricao_item, ItemAta.tipo_item, ItemAta.unidade_medida,
            Ata.numero_ata.label('num_ata'), Ata.ano.label('ano_ata'),
            Empenho.numero_empenho.label('documento_origem'),
            Empenho.data_emissao.label('data_documento'),
            ConsumoItemEmpenho.quantidade_consumida.label('qtd_consumida_total'),
            ConsumoItemEmpenho.valor_total_consumido_item.label('vlr_consumido_total')
        ).join(Empenho, ConsumoItemEmpenho.empenho_id == Empenho.id)\
         .join(ItemAta, ConsumoItemEmpenho.item_ata_id == ItemAta.id)\
         .join(Ata, ItemAta.ata_id == Ata.id)\
         .filter(Empenho.unidade_saude_id == unidade_id)

        if data_inicio:
            query_contratinhos = query_contratinhos.filter(Contratinho.data_emissao >= data_inicio)
            query_empenhos = query_empenhos.filter(Empenho.data_emissao >= data_inicio)
        if data_fim:
            data_fim_ajustada = data_fim + timedelta(days=1)
            query_contratinhos = query_contratinhos.filter(Contratinho.data_emissao < data_fim_ajustada)
            query_empenhos = query_empenhos.filter(Empenho.data_emissao < data_fim_ajustada)
        
        consumos_contratinhos = query_contratinhos.order_by(Contratinho.data_emissao.desc(), ItemAta.descricao_item).all()
        consumos_empenhos = query_empenhos.order_by(Empenho.data_emissao.desc(), ItemAta.descricao_item).all()
        
        dados_para_relatorio = []
        tipo_item_map = dict(ItemAta.TIPO_ITEM_CHOICES)

        for consumo in consumos_contratinhos:
            dados_para_relatorio.append({
                'item_descricao': consumo.descricao_item,
                'item_tipo': tipo_item_map.get(consumo.tipo_item, consumo.tipo_item),
                'item_unidade': consumo.unidade_medida,
                'ata_origem': f"{consumo.num_ata}/{consumo.ano_ata}",
                'documento_origem': f"CT: {consumo.documento_origem}", 
                'data_documento': consumo.data_documento.strftime('%d/%m/%Y') if consumo.data_documento else '-',
                'quantidade_consumida': consumo.qtd_consumida_total,
                'valor_total_consumido': consumo.vlr_consumido_total
            })
        
        for consumo in consumos_empenhos:
            dados_para_relatorio.append({
                'item_descricao': consumo.descricao_item,
                'item_tipo': tipo_item_map.get(consumo.tipo_item, consumo.tipo_item),
                'item_unidade': consumo.unidade_medida,
                'ata_origem': f"{consumo.num_ata}/{consumo.ano_ata}",
                'documento_origem': f"EMP: {consumo.documento_origem}", 
                'data_documento': consumo.data_documento.strftime('%d/%m/%Y') if consumo.data_documento else '-',
                'quantidade_consumida': consumo.qtd_consumida_total,
                'valor_total_consumido': consumo.vlr_consumido_total
            })
        
        dados_para_relatorio.sort(key=lambda x: datetime.strptime(x['data_documento'], '%d/%m/%Y'), reverse=True)

        if not dados_para_relatorio:
            flash('Nenhum consumo encontrado para os filtros selecionados.', 'info')
            return render_template('selecionar_relatorio_consumo_unidade.html', form=form, titulo_pagina="Relatório de Consumo por Unidade")

        return reports.gerar_pdf_consumo_por_unidade(unidade, dados_para_relatorio, data_inicio, data_fim)

    return render_template('selecionar_relatorio_consumo_unidade.html', form=form, titulo_pagina="Relatório de Consumo por Unidade")

@app.route('/relatorio/consumo_item', methods=['GET', 'POST'])
def relatorio_consumo_item():
    form = RelatorioConsumoPorItemForm()
    if form.validate_on_submit():
        item_ata_id = form.item_ata_id.data
        data_inicio = form.data_inicio.data
        data_fim = form.data_fim.data

        item_selecionado = db.session.get(ItemAta, item_ata_id)
        if not item_selecionado:
            flash('Item da Ata não encontrado.', 'danger')
            return redirect(url_for('relatorio_consumo_item'))

        consumos_por_unidade = {}

        query_ct = db.session.query(
            Contratinho.unidade_saude_id,
            UnidadeSaude.nome_unidade,
            func.sum(ConsumoItemContratinho.quantidade_consumida).label('total_qtd'),
            func.sum(ConsumoItemContratinho.valor_total_consumido_item).label('total_valor')
        ).join(ConsumoItemContratinho, Contratinho.id == ConsumoItemContratinho.contratinho_id)\
         .join(UnidadeSaude, Contratinho.unidade_saude_id == UnidadeSaude.id)\
         .filter(ConsumoItemContratinho.item_ata_id == item_ata_id)
        
        if data_inicio: query_ct = query_ct.filter(Contratinho.data_emissao >= data_inicio)
        if data_fim: 
            data_fim_ct_ajustada = data_fim + timedelta(days=1)
            query_ct = query_ct.filter(Contratinho.data_emissao < data_fim_ct_ajustada)
        
        resultados_ct = query_ct.group_by(Contratinho.unidade_saude_id, UnidadeSaude.nome_unidade).all()

        for unidade_id_ct, nome_unidade_ct, total_qtd_ct, total_valor_ct in resultados_ct:
            if unidade_id_ct not in consumos_por_unidade:
                consumos_por_unidade[unidade_id_ct] = {'nome_unidade': nome_unidade_ct, 'total_qtd': 0.0, 'total_valor': 0.0}
            consumos_por_unidade[unidade_id_ct]['total_qtd'] += total_qtd_ct or 0.0
            consumos_por_unidade[unidade_id_ct]['total_valor'] += total_valor_ct or 0.0

        query_emp = db.session.query(
            Empenho.unidade_saude_id,
            UnidadeSaude.nome_unidade,
            func.sum(ConsumoItemEmpenho.quantidade_consumida).label('total_qtd'),
            func.sum(ConsumoItemEmpenho.valor_total_consumido_item).label('total_valor')
        ).join(ConsumoItemEmpenho, Empenho.id == ConsumoItemEmpenho.empenho_id)\
         .join(UnidadeSaude, Empenho.unidade_saude_id == UnidadeSaude.id)\
         .filter(ConsumoItemEmpenho.item_ata_id == item_ata_id)

        if data_inicio: query_emp = query_emp.filter(Empenho.data_emissao >= data_inicio)
        if data_fim: 
            data_fim_emp_ajustada = data_fim + timedelta(days=1)
            query_emp = query_emp.filter(Empenho.data_emissao < data_fim_emp_ajustada)

        resultados_emp = query_emp.group_by(Empenho.unidade_saude_id, UnidadeSaude.nome_unidade).all()

        for unidade_id_emp, nome_unidade_emp, total_qtd_emp, total_valor_emp in resultados_emp:
            if unidade_id_emp not in consumos_por_unidade:
                consumos_por_unidade[unidade_id_emp] = {'nome_unidade': nome_unidade_emp, 'total_qtd': 0.0, 'total_valor': 0.0}
            consumos_por_unidade[unidade_id_emp]['total_qtd'] += total_qtd_emp or 0.0
            consumos_por_unidade[unidade_id_emp]['total_valor'] += total_valor_emp or 0.0
        
        dados_agregados_para_pdf = list(consumos_por_unidade.values())
        dados_agregados_para_pdf.sort(key=lambda x: x['nome_unidade']) 

        if not dados_agregados_para_pdf:
            flash(f'Nenhum consumo encontrado para o item "{item_selecionado.descricao_item}" nos filtros selecionados.', 'info')
            return render_template('selecionar_relatorio_consumo_item.html', form=form, titulo_pagina="Relatório de Consumo por Item")

        return reports.gerar_pdf_consumo_por_item(item_selecionado, dados_agregados_para_pdf, data_inicio, data_fim)

    return render_template('selecionar_relatorio_consumo_item.html', form=form, titulo_pagina="Relatório de Consumo por Item")


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    is_debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=is_debug_mode)