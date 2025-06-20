# Início do arquivo completo: app.py

import os
import csv
import io
import click
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.exc import IntegrityError
from wtforms.validators import ValidationError
from sqlalchemy import func, or_
import locale 
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
import math

# Importa a classe de configuração
from config import Config

from models import (
    db, User, Ata, Contrato, Contratinho, Empenho, ItemAta, UnidadeSaude,
    ConsumoItemContratinho, ConsumoItemEmpenho, ItemContrato, Aditivo, CotaUnidadeItem, Log, Comentario,
    Processo
)
from forms import (
    LoginForm, AtaForm, ContratoForm, ContratinhoForm, EmpenhoForm, ItemAtaForm, UnidadeSaudeForm,
    AdicionarItensLoteAtaForm, RelatorioConsumoUnidadeForm, RelatorioConsumoPorItemForm,
    RelatorioContratosVigentesUnidadeForm, AditivoForm, ImportCSVForm, GerenciarCotasForm,
    RelatorioPotencialDeSolicitacaoForm, UserCreationForm, UserEditForm, CommentForm,
    ProcessoForm
)
import reports

app = Flask(__name__)

app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def registrar_log(user, action, details=""):
    try:
        log_entry = Log(user_id=user.id, action=action, details=details)
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"ERRO AO REGISTRAR LOG: {e}")

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

@app.cli.command("create-admin")
@click.argument("username")
@click.argument("password")
def create_admin(username, password):
    """Cria um novo usuário admin ou redefine a senha de um usuário existente."""
    user = User.query.filter_by(username=username).first()
    if user:
        user.set_password(password)
        db.session.commit()
        print(f"A senha para o usuário existente '{username}' foi redefinida com sucesso!")
    else:
        admin_user = User(username=username, role='admin')
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Administrador '{username}' criado com sucesso!")

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        registrar_log(user, "LOGIN", f"Usuário '{user.username}' efetuou login.")
        return redirect(url_for('dashboard'))
    return render_template('login.html', titulo_pagina='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    registrar_log(current_user, "LOGOUT", f"Usuário '{current_user.username}' efetuou logout.")
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))

# --- ROTAS DE GESTÃO DE USUÁRIOS (ADMIN) ---
@app.route('/admin/usuarios')
@login_required
@role_required('admin')
def admin_listar_usuarios():
    users = User.query.order_by(User.username).all()
    return render_template('admin/listar_usuarios.html', users=users, titulo_pagina="Gerenciar Usuários")

@app.route('/admin/logs')
@login_required
@role_required('admin')
def admin_visualizar_logs():
    page = request.args.get('page', 1, type=int)
    logs = Log.query.order_by(Log.timestamp.desc()).paginate(page=page, per_page=25)
    return render_template('admin/visualizar_logs.html', logs=logs, titulo_pagina="Logs de Atividade")

@app.route('/admin/usuario/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_criar_usuario():
    form = UserCreationForm()
    if form.validate_on_submit():
        try:
            new_user = User(
                username=form.username.data,
                role=form.role.data,
                unidade_saude_id=form.unidade_saude_id.data if form.unidade_saude_id.data else None
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.commit()
            registrar_log(current_user, "CRIOU USUÁRIO", f"Usuário '{new_user.username}' (ID: {new_user.id}) criado com o perfil '{new_user.role}'.")
            flash(f'Usuário "{new_user.username}" criado com sucesso!', 'success')
            return redirect(url_for('admin_listar_usuarios'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Este nome de usuário já existe.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao criar o usuário: {e}', 'danger')
    return render_template('admin/form_usuario.html', form=form, titulo_pagina="Criar Novo Usuário", action="create")

@app.route('/admin/usuario/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_editar_usuario(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    
    form = UserEditForm(original_username=user.username)
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.role = form.role.data
            user.unidade_saude_id = form.unidade_saude_id.data if form.unidade_saude_id.data else None
            if form.password.data:
                user.set_password(form.password.data)
            db.session.commit()
            registrar_log(current_user, "EDITOU USUÁRIO", f"Usuário '{user.username}' (ID: {user.id}) foi atualizado.")
            flash(f'Usuário "{user.username}" atualizado com sucesso!', 'success')
            return redirect(url_for('admin_listar_usuarios'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Este nome de usuário já existe.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocorreu um erro ao editar o usuário: {e}', 'danger')

    elif request.method == 'GET':
        form.username.data = user.username
        form.role.data = user.role
        form.unidade_saude_id.data = user.unidade_saude_id
        
    return render_template('admin/form_usuario.html', form=form, titulo_pagina=f"Editar Usuário: {user.username}", user=user, action="edit")

@app.route('/admin/usuario/excluir/<int:user_id>', methods=['GET'])
@login_required
@role_required('admin')
def admin_excluir_usuario(user_id):
    user_to_delete = db.session.get(User, user_id)
    if not user_to_delete:
        flash('Usuário não encontrado.', 'warning')
        return redirect(url_for('admin_listar_usuarios'))

    if user_to_delete.id == current_user.id:
        flash('Você não pode excluir a si mesmo.', 'danger')
        return redirect(url_for('admin_listar_usuarios'))
    
    if user_to_delete.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Não é possível excluir o único administrador do sistema.', 'danger')
            return redirect(url_for('admin_listar_usuarios'))

    try:
        username = user_to_delete.username
        user_id_deleted = user_to_delete.id
        db.session.delete(user_to_delete)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU USUÁRIO", f"Usuário '{username}' (ID: {user_id_deleted}) foi excluído.")
        flash(f'Usuário "{username}" excluído com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o usuário: {e}', 'danger')
    
    return redirect(url_for('admin_listar_usuarios'))

# --- ROTA PARA O DASHBOARD ---
@app.route('/dashboard')
@login_required
def dashboard():
    totais = {
        'processos': Processo.query.count(),
        'atas': Ata.query.count(),
        'contratos': Contrato.query.count(),
        'contratinhos': Contratinho.query.count(),
        'empenhos': Empenho.query.count(),
        'itens_ata': ItemAta.query.count(),
        'unidades_saude': UnidadeSaude.query.count()
    }
    
    percentual_config_default = app.config.get('PERCENTUAL_SALDO_BAIXO', 20)
    try:
        percentual_alerta_atual = request.args.get('percentual_alerta', default=percentual_config_default, type=int)
        if not (1 <= percentual_alerta_atual <= 100):
            percentual_alerta_atual = percentual_config_default
    except (ValueError, TypeError):
        percentual_alerta_atual = percentual_config_default

    unidade_id_filtro = request.args.get('unidade_id_filtro', 'todas')
    percentual_limite = percentual_alerta_atual / 100.0
    
    itens_saldo_baixo = []
    if unidade_id_filtro == 'todas':
        itens_saldo_baixo = ItemAta.query.filter(
            ItemAta.quantidade_registrada > 0,
            (ItemAta.saldo_disponivel / ItemAta.quantidade_registrada) <= percentual_limite
        ).order_by(ItemAta.saldo_disponivel).all()
    else:
        try:
            unidade_id_int = int(unidade_id_filtro)
            cotas_saldo_baixo = CotaUnidadeItem.query.filter(
                CotaUnidadeItem.unidade_saude_id == unidade_id_int,
                CotaUnidadeItem.quantidade_prevista > 0,
                ((CotaUnidadeItem.quantidade_prevista - CotaUnidadeItem.quantidade_consumida) / CotaUnidadeItem.quantidade_prevista) <= percentual_limite
            ).all()
            for cota in cotas_saldo_baixo:
                saldo = cota.quantidade_prevista - cota.quantidade_consumida
                cota.saldo_percentual = (saldo / cota.quantidade_prevista) * 100 if cota.quantidade_prevista > 0 else 0
            itens_saldo_baixo = cotas_saldo_baixo
        except (ValueError, TypeError):
            flash("ID de Unidade inválido.", "danger")
            unidade_id_filtro = 'todas'

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
    filtro_vencidos = request.args.get('vencidos_dashboard', 'ocultar')
    query_atas = Ata.query.filter(Ata.data_validade != None, Ata.data_validade <= data_alerta_prazo_obj)
    query_contratos = Contrato.query.filter(Contrato.data_fim_vigencia != None, Contrato.data_fim_vigencia <= data_alerta_prazo_obj)
    query_contratinhos = Contratinho.query.filter(Contratinho.data_fim_vigencia != None, Contratinho.data_fim_vigencia <= data_alerta_prazo_obj)
    
    if filtro_vencidos == 'ocultar':
        query_atas = query_atas.filter(Ata.data_validade >= hoje_obj)
        query_contratos = query_contratos.filter(Contrato.data_fim_vigencia >= hoje_obj)
        query_contratinhos = query_contratinhos.filter(Contratinho.data_fim_vigencia >= hoje_obj)
        
    atas_vencendo = query_atas.order_by(Ata.data_validade).all()
    contratos_vencendo = query_contratos.order_by(Contrato.data_fim_vigencia).all()
    contratinhos_vencendo = query_contratinhos.order_by(Contratinho.data_fim_vigencia).all()
    
    recent_comments = Comentario.query.order_by(Comentario.timestamp.desc()).limit(5).all()

    return render_template('dashboard.html',
                           titulo_pagina="Dashboard",
                           totais=totais,
                           itens_saldo_baixo=itens_saldo_baixo,
                           percentual_alerta_atual=percentual_alerta_atual,
                           unidades_saude=UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all(),
                           unidade_id_filtro_atual=unidade_id_filtro,
                           atas_vencendo=atas_vencendo,
                           contratos_vencendo=contratos_vencendo,
                           contratinhos_vencendo=contratinhos_vencendo,
                           dias_alerta_prazo_atual=dias_prazo_atual, 
                           hoje_datetime=hoje_obj,
                           filtro_vencidos_ativo=filtro_vencidos,
                           recent_comments=recent_comments)

# --- ROTAS PARA PROCESSOS ---
@app.route('/processos')
@login_required
def listar_processos():
    processos = Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()
    return render_template('listar_processos.html',
                           titulo_pagina="Processos Administrativos",
                           lista_de_processos=processos)

@app.route('/processo/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def criar_processo():
    form = ProcessoForm()
    if form.validate_on_submit():
        try:
            novo_processo = Processo(
                numero_processo=form.numero_processo.data,
                ano=form.ano.data,
                descricao=form.descricao.data
            )
            db.session.add(novo_processo)
            db.session.commit()
            registrar_log(current_user, "CRIOU PROCESSO", f"Processo nº {novo_processo.numero_processo}/{novo_processo.ano} (ID: {novo_processo.id}) criado.")
            flash(f'Processo {novo_processo.numero_processo}/{novo_processo.ano} criado com sucesso!', 'success')
            return redirect(url_for('listar_processos'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um processo com este número e ano.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar processo: {e}', 'danger')
    return render_template('criar_processo.html', titulo_pagina="Criar Novo Processo", form=form)

@app.route('/processo/editar/<int:processo_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def editar_processo(processo_id):
    processo = Processo.query.get_or_404(processo_id)
    form = ProcessoForm(obj=processo)
    if form.validate_on_submit():
        try:
            form.populate_obj(processo)
            db.session.commit()
            registrar_log(current_user, "EDITOU PROCESSO", f"Processo nº {processo.numero_processo}/{processo.ano} (ID: {processo_id}) foi atualizado.")
            flash('Processo atualizado com sucesso!', 'success')
            return redirect(url_for('listar_processos'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um processo com este número e ano.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar processo: {e}', 'danger')
    return render_template('editar_processo.html', titulo_pagina="Editar Processo", form=form, processo=processo)

@app.route('/processo/visualizar/<int:processo_id>')
@login_required
def visualizar_processo(processo_id):
    processo = Processo.query.get_or_404(processo_id)
    return render_template('visualizar_processo.html',
                           titulo_pagina=f"Detalhes do Processo {processo.numero_processo}/{processo.ano}",
                           processo=processo)

@app.route('/processo/excluir/<int:processo_id>', methods=['GET'])
@login_required
@role_required('admin', 'gestor')
def excluir_processo(processo_id):
    processo = Processo.query.get_or_404(processo_id)
    if processo.atas.count() or processo.contratos.count() or processo.contratinhos.count() or processo.empenhos.count():
        flash('Não é possível excluir o processo. Existem Atas, Contratos ou outros documentos vinculados a ele.', 'danger')
        return redirect(url_for('listar_processos'))
    try:
        num_processo = processo.numero_processo
        ano_processo = processo.ano
        db.session.delete(processo)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU PROCESSO", f"Processo nº {num_processo}/{ano_processo} (ID: {processo_id}) foi excluído.")
        flash(f'Processo {num_processo}/{ano_processo} excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir processo: {e}', 'danger')
    return redirect(url_for('listar_processos'))


# --- ROTAS PARA ATAS ---
@app.route('/')
@app.route('/atas')
@login_required
def index():
    filtro = request.args.get('filtro', 'vigentes')
    query_base = Ata.query
    hoje = datetime.now(timezone.utc).date()
    if filtro == 'vigentes':
        query_base = query_base.filter(or_(Ata.data_validade >= hoje, Ata.data_validade == None))
    todas_as_atas = query_base.order_by(Ata.ano.desc(), Ata.numero_ata.desc()).all()
    return render_template('listar_atas.html',
                           titulo_pagina="Atas Registradas",
                           lista_de_atas=todas_as_atas,
                           filtro_ativo=filtro,
                           today=hoje)

@app.route('/importar/atas_csv', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def importar_atas_csv():
    form = ImportCSVForm()
    if form.validate_on_submit():
        if 'csv_file' not in request.files:
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
            
        if file and file.filename.endswith('.csv'):
            try:
                atas_criadas = {}
                stream = io.TextIOWrapper(file.stream, 'utf-8', errors='replace')
                csv_reader = csv.DictReader(stream)
                
                itens_criados_total = 0
                
                for row in csv_reader:
                    numero_ata = row.get('numero_ata')
                    ano_ata_str = row.get('ano_ata')

                    if not numero_ata or not ano_ata_str:
                        raise ValueError("Cada linha deve ter 'numero_ata' e 'ano_ata'.")

                    chave_ata = f"{numero_ata}/{ano_ata_str}"
                    ata_obj = atas_criadas.get(chave_ata)

                    if not ata_obj:
                        ata_obj = Ata.query.filter_by(numero_ata=numero_ata, ano=int(ano_ata_str)).first()
                        if not ata_obj:
                            data_assinatura = datetime.strptime(row['data_assinatura_ata'], '%d/%m/%Y') if row.get('data_assinatura_ata') else None
                            data_validade = datetime.strptime(row['data_validade_ata'], '%d/%m/%Y') if row.get('data_validade_ata') else None

                            ata_obj = Ata(
                                numero_ata=numero_ata,
                                ano=int(ano_ata_str),
                                descricao=row.get('descricao_ata'),
                                data_assinatura=data_assinatura,
                                data_validade=data_validade
                            )
                            db.session.add(ata_obj)
                            db.session.flush() 
                        
                        atas_criadas[chave_ata] = ata_obj

                    valor_unitario_str = row.get('valor_unitario_registrado', '0').replace(',', '.')
                    quantidade_str = row.get('quantidade_registrada', '0').replace(',', '.')
                    
                    novo_item = ItemAta(
                        ata_id=ata_obj.id,
                        descricao_item=row.get('descricao_item'),
                        tipo_item=row.get('tipo_item', 'OUTRO'),
                        unidade_medida=row.get('unidade_medida'),
                        quantidade_registrada=float(quantidade_str),
                        valor_unitario_registrado=float(valor_unitario_str),
                        lote=row.get('lote')
                    )
                    novo_item.saldo_disponivel = novo_item.quantidade_registrada
                    db.session.add(novo_item)
                    itens_criados_total += 1
                
                db.session.commit()
                registrar_log(current_user, "IMPORTAÇÃO CSV", f"{len(atas_criadas)} ata(s) e {itens_criados_total} item(ns) importados.")
                flash(f'Importação concluída com sucesso! {len(atas_criadas)} ata(s) processada(s) e {itens_criados_total} item(ns) criado(s).', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao processar o arquivo CSV: {e}', 'danger')

    return render_template('importar_atas_csv.html', form=form, titulo_pagina="Importar Atas de CSV")

@app.route('/ata/nova', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def criar_ata():
    form = AtaForm()
    if form.validate_on_submit():
        try:
            nova_ata_db = Ata(
                processo_id=form.processo_id.data,
                numero_ata=form.numero_ata.data, 
                ano=form.ano.data,
                descricao=form.descricao.data, 
                data_assinatura=form.data_assinatura.data,
                data_validade=form.data_validade.data
            )
            db.session.add(nova_ata_db)
            db.session.commit()
            registrar_log(current_user, "CRIOU ATA", f"Ata nº {nova_ata_db.numero_ata}/{nova_ata_db.ano} (ID: {nova_ata_db.id}) criada.")
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
@login_required
@role_required('admin', 'gestor')
def editar_ata(ata_id):
    ata_para_editar = Ata.query.get_or_404(ata_id)
    form = AtaForm(obj=ata_para_editar)
    if form.validate_on_submit():
        try:
            form.populate_obj(ata_para_editar)
            db.session.commit()
            registrar_log(current_user, "EDITOU ATA", f"Ata nº {ata_para_editar.numero_ata}/{ata_para_editar.ano} (ID: {ata_id}) foi atualizada.")
            flash('Ata atualizada com sucesso!', 'success')
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe uma ata com este número. Verifique os dados.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar ata: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.processo_id.data = ata_para_editar.processo_id

    return render_template('editar_ata.html', titulo_pagina="Editar Ata", form=form, ata_id=ata_id)

@app.route('/ata/excluir/<int:ata_id>', methods=['GET'])
@login_required
@role_required('admin', 'gestor')
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
        
        num_ata = ata_para_excluir.numero_ata
        ano_ata = ata_para_excluir.ano
        
        for item_ata in list(ata_para_excluir.itens_ata): 
            db.session.delete(item_ata)
        db.session.delete(ata_para_excluir)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU ATA", f"Ata nº {num_ata}/{ano_ata} (ID: {ata_id}) e todos os seus itens foram excluídos.")
        flash('Ata e todos os seus itens foram excluídos com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir ata: {str(e)}. Verifique as dependências.', 'danger')
        app.logger.error(f"Erro ao excluir ata {ata_id}: {e}", exc_info=True)
    return redirect(url_for('index'))

@app.route('/ata/<int:ata_id>/itens')
@login_required
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
@login_required
def itens_da_ata_json(ata_id):
    try:
        ata = db.session.get(Ata, ata_id)
        if not ata:
            return jsonify({'error': 'Ata não encontrada'}), 404
        
        itens_query = ItemAta.query.filter_by(ata_id=ata_id).order_by(ItemAta.descricao_item).all()
        
        itens_list = []
        if not itens_query:
            itens_list.append({'id': '', 'text': 'Nenhum item cadastrado para esta Ata'})
        else:
            itens_list.append({'id': '', 'text': '--- Selecione um Item ---'})
            for item in itens_query:
                saldo_txt = f"Saldo: {format_quantity_filter(item.saldo_disponivel)}"
                vu_txt = f"VU: {format_br_currency_filter(item.valor_unitario_registrado)}"
                itens_list.append({
                    'id': item.id,
                    'text': f"{item.descricao_item} ({saldo_txt}, {vu_txt})"
                })

        return jsonify({
            'itens': itens_list,
            'ata_descricao': ata.descricao or "Ata sem descrição."
        })
    except Exception as e:
        app.logger.error(f"Erro ao buscar itens da ata {ata_id} via JSON: {e}", exc_info=True)
        return jsonify({'error': 'Erro interno ao processar a solicitação.'}), 500

@app.route('/ata/<int:ata_id>/item/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
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
            registrar_log(current_user, "CRIOU ITEM DE ATA", f"Item '{novo_item.descricao_item}' (ID: {novo_item.id}) adicionado à Ata ID {ata_id}.")
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
@login_required
@role_required('admin', 'gestor')
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
                registrar_log(current_user, "ADICIONOU ITENS EM LOTE", f"{novos_itens_criados} itens adicionados à Ata ID {ata.id}.")
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
@login_required
@role_required('admin', 'gestor')
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
                registrar_log(current_user, "EDITOU ITEM DE ATA", f"Item ID {item_id} da Ata ID {ata_id} foi atualizado.")
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

@app.route('/item_ata/<int:item_id>/gerenciar_cotas', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def gerenciar_cotas_item(item_id):
    item = ItemAta.query.get_or_404(item_id)
    unidades = UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()
    form = GerenciarCotasForm()

    if form.validate_on_submit():
        soma_cotas = sum(cota_data.get('quantidade_prevista', 0.0) or 0.0 for cota_data in form.cotas.data)

        if soma_cotas > item.quantidade_registrada:
            flash(f'A soma das cotas ({soma_cotas}) não pode ultrapassar a quantidade total registrada do item ({item.quantidade_registrada}).', 'danger')
        else:
            try:
                for cota_data in form.cotas.data:
                    unidade_id = cota_data['unidade_saude_id']
                    quantidade = cota_data.get('quantidade_prevista') or 0.0
                    
                    cota_existente = CotaUnidadeItem.query.filter_by(
                        item_ata_id=item.id,
                        unidade_saude_id=unidade_id
                    ).first()

                    if cota_existente:
                        cota_existente.quantidade_prevista = quantidade
                    elif quantidade > 0:
                        nova_cota = CotaUnidadeItem(
                            item_ata_id=item.id,
                            unidade_saude_id=unidade_id,
                            quantidade_prevista=quantidade
                        )
                        db.session.add(nova_cota)
                db.session.commit()
                registrar_log(current_user, "GERENCIOU COTAS", f"Cotas do Item ID {item_id} foram atualizadas.")
                flash('Cotas salvas com sucesso!', 'success')
                return redirect(url_for('listar_itens_da_ata', ata_id=item.ata_id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao salvar as cotas: {e}', 'danger')

    if not form.cotas.data: 
        cotas_existentes = {c.unidade_saude_id: c for c in item.cotas}
        for unidade in unidades:
            cota_existente = cotas_existentes.get(unidade.id)
            form.cotas.append_entry({
                'unidade_saude_id': unidade.id,
                'quantidade_prevista': cota_existente.quantidade_prevista if cota_existente else 0.0
            })

    return render_template('gerenciar_cotas_item.html', 
                           item=item, 
                           form=form, 
                           unidades=unidades)

@app.route('/item_ata/<int:item_id>/visualizar_cotas')
@login_required
def visualizar_cotas_item(item_id):
    item = ItemAta.query.get_or_404(item_id)
    cotas = CotaUnidadeItem.query.filter_by(item_ata_id=item.id).order_by(CotaUnidadeItem.unidade_saude_id).all()
    
    total_alocado = sum(c.quantidade_prevista for c in cotas)
    
    cotas_info = []
    for cota in cotas:
        saldo = cota.quantidade_prevista - cota.quantidade_consumida
        progresso = (cota.quantidade_consumida / cota.quantidade_prevista * 100) if cota.quantidade_prevista > 0 else -1
        
        cotas_info.append({
            'unidade_nome': cota.unidade_saude.nome_unidade,
            'previsto': cota.quantidade_prevista,
            'consumido': cota.quantidade_consumida,
            'saldo': saldo,
            'progresso': progresso
        })

    return render_template('visualizar_cotas_item.html',
                           item=item,
                           cotas_info=cotas_info,
                           total_alocado=total_alocado)

@app.route('/ata/<int:ata_id>/item/<int:item_id>/excluir', methods=['GET'])
@login_required
@role_required('admin', 'gestor')
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
        desc_item = item_para_excluir.descricao_item
        db.session.delete(item_para_excluir)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU ITEM DE ATA", f"Item '{desc_item}' (ID: {item_id}) foi excluído da Ata ID {ata_id}.")
        flash('Item da ata excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir item da ata: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir item da ata {item_id}: {e}", exc_info=True)
    return redirect(url_for('listar_itens_da_ata', ata_id=ata.id))

# --- LÓGICA AUXILIAR PARA PROCESSAR ITENS LIVRES ---
def _processar_itens_livres_contrato(form_itens_data, contrato_pai_obj):
    valor_total_dos_itens_calculado = 0.0
    for item_data in form_itens_data:
        descricao = item_data.get('descricao')
        if not descricao or not descricao.strip():
            continue

        try:
            quantidade = float(item_data.get('quantidade', 0))
            valor_unitario = float(item_data.get('valor_unitario', 0))
        except (ValueError, TypeError):
            continue

        if quantidade > 0:
            valor_total_deste_item = quantidade * valor_unitario
            valor_total_dos_itens_calculado += valor_total_deste_item
            novo_item_obj = ItemContrato(
                contrato_id=contrato_pai_obj.id,
                descricao=descricao,
                unidade_medida=item_data.get('unidade_medida'),
                quantidade=quantidade,
                valor_unitario=valor_unitario,
                valor_total_item=valor_total_deste_item
            )
            db.session.add(novo_item_obj)
            
    return valor_total_dos_itens_calculado

# --- ROTAS PARA CONTRATOS ---
@app.route('/contratos')
@login_required
def listar_contratos():
    filtro = request.args.get('filtro', 'vigentes')
    query_base = Contrato.query
    hoje = datetime.now(timezone.utc).date()
    if filtro == 'vigentes':
        query_base = query_base.filter(or_(Contrato.data_fim_vigencia >= hoje, Contrato.data_fim_vigencia == None))
    todos_os_contratos = query_base.order_by(Contrato.data_assinatura_contrato.desc(), Contrato.numero_contrato.desc()).all()
    return render_template('listar_contratos.html',
                           titulo_pagina="Lista de Contratos",
                           lista_de_contratos=todos_os_contratos,
                           filtro_ativo=filtro,
                           today=hoje)

@app.route('/contrato/visualizar/<int:contrato_id>')
@login_required
def visualizar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    comment_form = CommentForm()
    return render_template('visualizar_contrato.html',
                           titulo_pagina=f"Detalhes do Contrato {contrato.numero_contrato}",
                           contrato=contrato,
                           comment_form=comment_form)

@app.route('/contrato/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def criar_contrato():
    form = ContratoForm()
    if form.validate_on_submit():
        try:
            novo_contrato_db = Contrato(
                processo_id=form.processo_id.data,
                numero_contrato=form.numero_contrato.data,
                objeto=form.objeto.data,
                fornecedor=form.fornecedor.data,
                data_assinatura_contrato=form.data_assinatura_contrato.data,
                data_inicio_vigencia=form.data_inicio_vigencia.data,
                data_fim_vigencia=form.data_fim_vigencia.data,
                data_fim_vigencia_original=form.data_fim_vigencia.data,
                unidade_saude_id=form.unidade_saude_id.data
            )
            db.session.add(novo_contrato_db)
            db.session.flush() 
            
            valor_calculado_dos_itens = _processar_itens_livres_contrato(
                form.itens_contratados.data, novo_contrato_db
            )
            novo_contrato_db.valor_global_contrato = valor_calculado_dos_itens
            
            db.session.commit()
            registrar_log(current_user, "CRIOU CONTRATO", f"Contrato nº {novo_contrato_db.numero_contrato} (ID: {novo_contrato_db.id}) criado.")
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
@login_required
@role_required('admin', 'gestor')
def editar_contrato(contrato_id):
    contrato_para_editar = Contrato.query.get_or_404(contrato_id)
    if request.method == 'POST':
        form = ContratoForm(request.form)
    else:
        form = ContratoForm(obj=contrato_para_editar)
        form.processo_id.data = contrato_para_editar.processo_id
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

            contrato_para_editar.processo_id = form.processo_id.data
            contrato_para_editar.numero_contrato = form.numero_contrato.data
            contrato_para_editar.objeto = form.objeto.data
            contrato_para_editar.fornecedor = form.fornecedor.data
            contrato_para_editar.data_assinatura_contrato = form.data_assinatura_contrato.data
            contrato_para_editar.data_inicio_vigencia = form.data_inicio_vigencia.data
            contrato_para_editar.data_fim_vigencia = form.data_fim_vigencia.data 
            contrato_para_editar.data_fim_vigencia_original = form.data_fim_vigencia.data
            contrato_para_editar.unidade_saude_id=form.unidade_saude_id.data
            
            valor_calculado_dos_itens = _processar_itens_livres_contrato(
                form.itens_contratados.data, contrato_para_editar
            )
            contrato_para_editar.valor_global_contrato = valor_calculado_dos_itens
            
            _recalculate_contract_state(contrato_id)
            
            db.session.commit()
            registrar_log(current_user, "EDITOU CONTRATO", f"Contrato nº {contrato_para_editar.numero_contrato} (ID: {contrato_id}) foi atualizado.")
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
@login_required
@role_required('admin', 'gestor')
def excluir_contrato(contrato_id):
    contrato_para_excluir = Contrato.query.get_or_404(contrato_id)
    try:
        contrato_num = contrato_para_excluir.numero_contrato
        db.session.delete(contrato_para_excluir)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU CONTRATO", f"Contrato nº {contrato_num} (ID: {contrato_id}) foi excluído.")
        flash('Contrato excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contrato: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir contrato {contrato_id}: {e}", exc_info=True)
    return redirect(url_for('listar_contratos'))

# --- FUNÇÃO AUXILIAR PARA ADITIVOS ---
def _recalculate_contract_state(contrato_id):
    contrato = db.session.get(Contrato, contrato_id)
    if not contrato:
        return

    valor_base = sum(item.valor_total_item for item in contrato.itens_do_contrato.all() if item.valor_total_item is not None)
    acrescimo_aditivos = sum(ad.valor_acrescimo for ad in contrato.aditivos if ad.valor_acrescimo is not None)
    contrato.valor_global_contrato = valor_base + acrescimo_aditivos

    data_final = contrato.data_fim_vigencia_original
    
    aditivos_ordenados = sorted(list(contrato.aditivos), key=lambda ad: ad.data_assinatura.date() if isinstance(ad.data_assinatura, datetime) else ad.data_assinatura)

    for aditivo in aditivos_ordenados:
        if aditivo.nova_data_fim_vigencia:
            data_final = aditivo.nova_data_fim_vigencia
        elif aditivo.prazo_adicional_dias and data_final:
            current_date_obj = data_final.date() if isinstance(data_final, datetime) else data_final
            data_final = current_date_obj + timedelta(days=aditivo.prazo_adicional_dias)
    
    contrato.data_fim_vigencia = data_final

# --- ROTAS PARA ADITIVOS ---
@app.route('/contrato/<int:contrato_id>/aditivo/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def criar_aditivo(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    form = AditivoForm()
    if form.validate_on_submit():
        try:
            novo_aditivo = Aditivo(contrato_id=contrato.id)
            form.populate_obj(novo_aditivo)
            db.session.add(novo_aditivo)
            db.session.flush()
            
            _recalculate_contract_state(contrato_id)

            db.session.commit()
            registrar_log(current_user, "CRIOU ADITIVO", f"Aditivo nº {novo_aditivo.numero_aditivo} criado para o Contrato ID {contrato_id}.")
            flash('Termo Aditivo registrado e aplicado ao contrato com sucesso!', 'success')
            return redirect(url_for('visualizar_contrato', contrato_id=contrato.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar aditivo: {str(e)}', 'danger')
            app.logger.error(f"Erro ao criar aditivo para contrato {contrato_id}: {e}", exc_info=True)
    return render_template('criar_aditivo.html',
                           titulo_pagina="Adicionar Termo Aditivo",
                           form=form,
                           contrato=contrato)

@app.route('/aditivo/<int:aditivo_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def editar_aditivo(aditivo_id):
    aditivo = Aditivo.query.get_or_404(aditivo_id)
    contrato = aditivo.contrato_pai
    form = AditivoForm(obj=aditivo)
    if form.validate_on_submit():
        try:
            form.populate_obj(aditivo)
            
            _recalculate_contract_state(contrato.id)

            db.session.commit()
            registrar_log(current_user, "EDITOU ADITIVO", f"Aditivo nº {aditivo.numero_aditivo} (ID: {aditivo_id}) foi atualizado.")
            flash('Termo Aditivo atualizado com sucesso!', 'success')
            return redirect(url_for('visualizar_contrato', contrato_id=contrato.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao editar aditivo: {str(e)}', 'danger')
    return render_template('editar_aditivo.html',
                           titulo_pagina="Editar Termo Aditivo",
                           form=form,
                           aditivo=aditivo)

@app.route('/aditivo/<int:aditivo_id>/excluir', methods=['GET'])
@login_required
@role_required('admin', 'gestor')
def excluir_aditivo(aditivo_id):
    aditivo = Aditivo.query.get_or_404(aditivo_id)
    contrato_id = aditivo.contrato_id 
    try:
        aditivo_num = aditivo.numero_aditivo
        db.session.delete(aditivo)
        db.session.flush()

        _recalculate_contract_state(contrato_id)

        db.session.commit()
        registrar_log(current_user, "EXCLUIU ADITIVO", f"Aditivo nº {aditivo_num} (ID: {aditivo_id}) do Contrato ID {contrato_id} foi excluído.")
        flash('Termo Aditivo excluído. O valor e o prazo do contrato foram recalculados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir aditivo: {str(e)}', 'danger')
    return redirect(url_for('visualizar_contrato', contrato_id=contrato_id))


# --- ROTAS PARA UNIDADES DE SAÚDE ---
@app.route('/unidades')
@login_required
def listar_unidades():
    unidades = UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()
    unidade_tipo_map = dict(UnidadeSaude.TIPO_UNIDADE_CHOICES)
    return render_template('listar_unidades.html', 
                           titulo_pagina="Unidades de Saúde", 
                           unidades=unidades,
                           unidade_tipo_map=unidade_tipo_map)

@app.route('/unidade/nova', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def criar_unidade():
    form = UnidadeSaudeForm()
    if form.validate_on_submit():
        try:
            nova_unidade = UnidadeSaude()
            form.populate_obj(nova_unidade)
            db.session.add(nova_unidade)
            db.session.commit()
            registrar_log(current_user, "CRIOU UNIDADE", f"Unidade de Saúde '{nova_unidade.nome_unidade}' (ID: {nova_unidade.id}) criada.")
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
@login_required
@role_required('admin')
def editar_unidade(unidade_id):
    unidade_para_editar = UnidadeSaude.query.get_or_404(unidade_id)
    form = UnidadeSaudeForm(obj=unidade_para_editar)
    if form.validate_on_submit():
        try:
            form.populate_obj(unidade_para_editar)
            db.session.commit()
            registrar_log(current_user, "EDITOU UNIDADE", f"Unidade de Saúde '{unidade_para_editar.nome_unidade}' (ID: {unidade_id}) foi atualizada.")
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
@login_required
@role_required('admin')
def excluir_unidade(unidade_id):
    unidade_para_excluir = UnidadeSaude.query.get_or_404(unidade_id)
    if unidade_para_excluir.contratinhos_vinculados.first() or unidade_para_excluir.empenhos_vinculados.first() or unidade_para_excluir.contratos_vinculados.first():
        flash('Esta Unidade de Saúde não pode ser excluída pois está vinculada a Contratos, Contratinhos ou Empenhos.', 'danger')
        return redirect(url_for('listar_unidades'))
    try:
        unidade_nome = unidade_para_excluir.nome_unidade
        db.session.delete(unidade_para_excluir)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU UNIDADE", f"Unidade de Saúde '{unidade_nome}' (ID: {unidade_id}) foi excluída.")
        flash('Unidade de Saúde excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir unidade: {str(e)}', 'danger')
    return redirect(url_for('listar_unidades'))

# --- LÓGICA AUXILIAR PARA PROCESSAR ITENS CONSUMIDOS ---
def _processar_itens_consumidos_para_salvar(form_itens_data, objeto_pai, ModeloConsumoItem, ata_id_principal, unidade_saude_id):
    novos_consumos_db_list = []
    valor_total_itens_calculado = 0.0
    itens_a_processar = []
    if isinstance(form_itens_data, list):
        itens_a_processar = form_itens_data
    elif isinstance(form_itens_data, dict) and form_itens_data.get('item_ata_id'): 
        itens_a_processar = [form_itens_data]

    if not unidade_saude_id:
        raise ValueError("Uma Unidade de Saúde é obrigatória para consumir um item.")

    for item_data in itens_a_processar:
        item_id = int(item_data.get('item_ata_id')) if item_data.get('item_ata_id') else None
        quantidade_a_consumir = float(str(item_data.get('quantidade_consumida', '0.0')))
        
        if item_id and quantidade_a_consumir > 0:
            item_ata = db.session.get(ItemAta, item_id)
            if not item_ata:
                raise ValueError(f"Item ID {item_id} não encontrado.")

            if item_ata.ata_id != ata_id_principal:
                 raise ValueError(f"Item '{item_ata.descricao_item}' não pertence à Ata selecionada.")

            if item_ata.saldo_disponivel < quantidade_a_consumir:
                raise ValueError(f"Saldo GLOBAL insuficiente para '{item_ata.descricao_item}'. Disponível: {item_ata.saldo_disponivel:.2f}, Solicitado: {quantidade_a_consumir:.2f}.")

            cota_unidade = CotaUnidadeItem.query.filter_by(item_ata_id=item_id, unidade_saude_id=unidade_saude_id).first()
            if not cota_unidade or cota_unidade.quantidade_prevista == 0:
                unidade_nome = db.session.get(UnidadeSaude, unidade_saude_id).nome_unidade
                raise ValueError(f"A unidade '{unidade_nome}' não tem cota definida para o item '{item_ata.descricao_item}'.")
            
            saldo_cota = cota_unidade.quantidade_prevista - cota_unidade.quantidade_consumida
            if quantidade_a_consumir > saldo_cota:
                raise ValueError(f"Saldo da COTA da unidade insuficiente para '{item_ata.descricao_item}'. Saldo da Cota: {saldo_cota:.2f}, Solicitado: {quantidade_a_consumir:.2f}.")

            item_ata.saldo_disponivel -= quantidade_a_consumir
            cota_unidade.quantidade_consumida += quantidade_a_consumir
            
            valor_unit = item_ata.valor_unitario_registrado or 0.0
            valor_item_consumido = quantidade_a_consumir * valor_unit
            valor_total_itens_calculado += valor_item_consumido
            
            consumo_kwargs = {
                'item_ata_id': item_ata.id,
                'quantidade_consumida': quantidade_a_consumir,
                'valor_unitario_no_consumo': valor_unit,
                'valor_total_consumido_item': valor_item_consumido
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
@login_required
def listar_contratinhos():
    filtro = request.args.get('filtro', 'vigentes')
    query_base = Contratinho.query
    hoje = datetime.now(timezone.utc).date()
    if filtro == 'vigentes':
        query_base = query_base.filter(or_(Contratinho.data_fim_vigencia >= hoje, Contratinho.data_fim_vigencia == None))
    todos_os_contratinhos = query_base.order_by(Contratinho.data_emissao.desc()).all()
    return render_template('listar_contratinhos.html',
                           titulo_pagina="Lista de Contratinhos",
                           lista_de_contratinhos=todos_os_contratinhos,
                           filtro_ativo=filtro,
                           today=hoje)

@app.route('/contratinho/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def criar_contratinho():
    form = ContratinhoForm() 
    id_ata_para_choices = form.ata_id.data if form.ata_id.data is not None else None
    _helper_popula_choices_itens_subform(form, form.itens_consumidos, id_ata_para_choices)
    if form.validate_on_submit():
        try:
            novo_contratinho = Contratinho(
                processo_id=form.processo_id.data,
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
            _, valor_total_calculado_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, novo_contratinho, ConsumoItemContratinho, novo_contratinho.ata_id, novo_contratinho.unidade_saude_id
            )
            novo_contratinho.valor_total_itens = valor_total_calculado_dos_itens
            db.session.commit()
            registrar_log(current_user, "CRIOU CONTRATINHO", f"Contratinho nº {novo_contratinho.numero_contratinho} (ID: {novo_contratinho.id}) criado.")
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
@login_required
def visualizar_contratinho(contratinho_id):
    contratinho = Contratinho.query.get_or_404(contratinho_id)
    tipo_item_display_map = dict(ItemAta.TIPO_ITEM_CHOICES) 
    comment_form = CommentForm()
    return render_template('visualizar_contratinho.html',
                           titulo_pagina=f"Detalhes do Contratinho {contratinho.numero_contratinho}",
                           contratinho=contratinho,
                           tipo_item_display_map=tipo_item_display_map,
                           comment_form=comment_form)

@app.route('/contratinho/editar/<int:contratinho_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def editar_contratinho(contratinho_id):
    ct_para_editar = Contratinho.query.get_or_404(contratinho_id)
    if request.method == 'POST':
        form = ContratinhoForm(request.form)
    else:
        form = ContratinhoForm(obj=ct_para_editar)
        form.processo_id.data = ct_para_editar.processo_id
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
                cota_antiga = CotaUnidadeItem.query.filter_by(item_ata_id=consumo_antigo.item_ata_id, unidade_saude_id=ct_para_editar.unidade_saude_id).first()
                if item_ata_antigo:
                    item_ata_antigo.saldo_disponivel += consumo_antigo.quantidade_consumida
                if cota_antiga:
                    cota_antiga.quantidade_consumida -= consumo_antigo.quantidade_consumida
            for consumo_antigo in list(ct_para_editar.itens_consumidos): 
                 db.session.delete(consumo_antigo)
            db.session.flush() 
            ct_para_editar.processo_id = form.processo_id.data
            ct_para_editar.numero_contratinho = form.numero_contratinho.data
            ct_para_editar.objeto = form.objeto.data
            ct_para_editar.favorecido = form.favorecido.data
            ct_para_editar.data_emissao = form.data_emissao.data
            ct_para_editar.data_fim_vigencia = form.data_fim_vigencia.data
            ct_para_editar.ata_id = form.ata_id.data
            ct_para_editar.unidade_saude_id = form.unidade_saude_id.data
            ct_para_editar.valor_total_manual = form.valor_total_manual.data
            _, novo_valor_total_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, ct_para_editar, ConsumoItemContratinho, ct_para_editar.ata_id, ct_para_editar.unidade_saude_id
            )
            ct_para_editar.valor_total_itens = novo_valor_total_dos_itens
            db.session.commit()
            registrar_log(current_user, "EDITOU CONTRATINHO", f"Contratinho nº {ct_para_editar.numero_contratinho} (ID: {ct_para_editar.id}) foi atualizado.")
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
@login_required
@role_required('admin', 'gestor')
def excluir_contratinho(contratinho_id):
    ct_para_excluir = Contratinho.query.get_or_404(contratinho_id)
    try:
        ct_num = ct_para_excluir.numero_contratinho
        for consumo in ct_para_excluir.itens_consumidos:
            item_afetado = db.session.get(ItemAta, consumo.item_ata_id)
            cota_afetada = CotaUnidadeItem.query.filter_by(item_ata_id=consumo.item_ata_id, unidade_saude_id=ct_para_excluir.unidade_saude_id).first()
            if item_afetado:
                item_afetado.saldo_disponivel += consumo.quantidade_consumida
            if cota_afetada:
                cota_afetada.quantidade_consumida -= consumo.quantidade_consumida
        db.session.delete(ct_para_excluir)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU CONTRATINHO", f"Contratinho nº {ct_num} (ID: {contratinho_id}) foi excluído.")
        flash('Contratinho excluído com sucesso! Saldos dos itens e das cotas foram restaurados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contratinho: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir contratinho {contratinho_id}: {e}", exc_info=True)
    return redirect(url_for('listar_contratinhos'))

# --- ROTAS PARA EMPENHOS ---
@app.route('/empenhos')
@login_required
def listar_empenhos():
    todos_os_empenhos = Empenho.query.order_by(Empenho.data_emissao.desc()).all()
    return render_template('listar_empenhos.html',
                           titulo_pagina="Lista de Empenhos",
                           lista_de_empenhos=todos_os_empenhos)

@app.route('/empenho/visualizar/<int:empenho_id>') 
@login_required
def visualizar_empenho(empenho_id):
    empenho = Empenho.query.get_or_404(empenho_id)
    tipo_item_display_map = dict(ItemAta.TIPO_ITEM_CHOICES)
    comment_form = CommentForm()
    return render_template('visualizar_empenho.html',
                           titulo_pagina=f"Detalhes do Empenho {empenho.numero_empenho}",
                           empenho=empenho,
                           tipo_item_display_map=tipo_item_display_map,
                           comment_form=comment_form)

@app.route('/empenho/novo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'gestor')
def criar_empenho():
    form = EmpenhoForm()
    id_ata_para_choices = form.ata_id.data if form.ata_id.data is not None else None
    _helper_popula_choices_itens_subform(form, form.itens_consumidos, id_ata_para_choices)
    if form.validate_on_submit():
        try:
            novo_empenho = Empenho(
                processo_id=form.processo_id.data,
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
            _, valor_total_calculado_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, novo_empenho, ConsumoItemEmpenho, novo_empenho.ata_id, novo_empenho.unidade_saude_id
            )
            novo_empenho.valor_total_itens = valor_total_calculado_dos_itens
            db.session.commit()
            registrar_log(current_user, "CRIOU EMPENHO", f"Empenho nº {novo_empenho.numero_empenho} (ID: {novo_empenho.id}) criado.")
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
@login_required
@role_required('admin', 'gestor')
def editar_empenho(empenho_id):
    emp_para_editar = Empenho.query.get_or_404(empenho_id)
    if request.method == 'POST':
        form = EmpenhoForm(request.form)
    else:
        form = EmpenhoForm(obj=emp_para_editar)
        form.processo_id.data = emp_para_editar.processo_id
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
                cota_antiga = CotaUnidadeItem.query.filter_by(item_ata_id=consumo_antigo.item_ata_id, unidade_saude_id=emp_para_editar.unidade_saude_id).first()
                if item_ata_antigo:
                    item_ata_antigo.saldo_disponivel += consumo_antigo.quantidade_consumida
                if cota_antiga:
                    cota_antiga.quantidade_consumida -= consumo_antigo.quantidade_consumida
            for consumo_antigo in list(emp_para_editar.itens_consumidos):
                db.session.delete(consumo_antigo)
            db.session.flush()

            emp_para_editar.processo_id = form.processo_id.data
            emp_para_editar.numero_empenho = form.numero_empenho.data
            emp_para_editar.descricao_simples = form.descricao_simples.data
            emp_para_editar.favorecido = form.favorecido.data
            emp_para_editar.data_emissao = form.data_emissao.data
            emp_para_editar.ata_id = form.ata_id.data
            emp_para_editar.unidade_saude_id = form.unidade_saude_id.data
            emp_para_editar.valor_total_manual = form.valor_total_manual.data
            id_ata_para_processar_itens = form.ata_id.data if form.ata_id.data else emp_para_editar.ata_id
            _, novo_valor_total_dos_itens = _processar_itens_consumidos_para_salvar(
                form.itens_consumidos.data, emp_para_editar, ConsumoItemEmpenho, id_ata_para_processar_itens, emp_para_editar.unidade_saude_id
            )
            emp_para_editar.valor_total_itens = novo_valor_total_dos_itens
            
            db.session.commit()
            registrar_log(current_user, "EDITOU EMPENHO", f"Empenho nº {emp_para_editar.numero_empenho} (ID: {empenho_id}) foi atualizado.")
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
@login_required
@role_required('admin', 'gestor')
def excluir_empenho(empenho_id):
    emp_para_excluir = Empenho.query.get_or_404(empenho_id)
    try:
        emp_num = emp_para_excluir.numero_empenho
        for consumo in emp_para_excluir.itens_consumidos:
            item_afetado = db.session.get(ItemAta, consumo.item_ata_id)
            cota_afetada = CotaUnidadeItem.query.filter_by(item_ata_id=consumo.item_ata_id, unidade_saude_id=emp_para_excluir.unidade_saude_id).first()
            if item_afetado:
                item_afetado.saldo_disponivel += consumo.quantidade_consumida
            if cota_afetada:
                cota_afetada.quantidade_consumida -= consumo.quantidade_consumida
        db.session.delete(emp_para_excluir)
        db.session.commit()
        registrar_log(current_user, "EXCLUIU EMPENHO", f"Empenho nº {emp_num} (ID: {empenho_id}) foi excluído.")
        flash('Empenho excluído com sucesso! Saldos dos itens e das cotas foram restaurados.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir empenho: {str(e)}', 'danger')
        app.logger.error(f"Erro ao excluir empenho {empenho_id}: {e}", exc_info=True)
    return redirect(url_for('listar_empenhos'))

# --- ROTA PARA ADICIONAR COMENTÁRIOS ---
@app.route('/comentario/adicionar/<string:doc_tipo>/<int:doc_id>', methods=['POST'])
@login_required
def adicionar_comentario(doc_tipo, doc_id):
    form = CommentForm()
    
    model_map = {
        'Ata': Ata,
        'Contrato': Contrato,
        'Contratinho': Contratinho,
        'Empenho': Empenho,
        'Aditivo': Aditivo
    }
    ModelClass = model_map.get(doc_tipo)

    if not ModelClass:
        flash('Tipo de documento inválido para comentário.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    documento = db.session.get(ModelClass, doc_id)
    if not documento:
        flash('Documento não encontrado.', 'danger')
        return redirect(request.referrer or url_for('dashboard'))

    if form.validate_on_submit():
        novo_comentario = Comentario(
            content=form.content.data,
            user_id=current_user.id,
            commentable_id=documento.id,
            commentable_type=doc_tipo
        )
        db.session.add(novo_comentario)
        db.session.commit()
        registrar_log(current_user, f"ADICIONOU COMENTÁRIO", f"Comentário adicionado ao {doc_tipo} ID {doc_id}.")
        flash('Comentário adicionado com sucesso!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return redirect(request.referrer or url_for('dashboard'))

# --- ROTAS DE API PARA GRÁFICOS ---
@app.route('/api/gastos_por_unidade')
@login_required
def api_gastos_por_unidade():
    gastos = {}

    # Consulta para Contratinhos
    gastos_contratinhos = db.session.query(
        UnidadeSaude.nome_unidade,
        func.sum(ConsumoItemContratinho.valor_total_consumido_item)
    ).join(Contratinho, Contratinho.unidade_saude_id == UnidadeSaude.id)\
     .join(ConsumoItemContratinho, ConsumoItemContratinho.contratinho_id == Contratinho.id)\
     .group_by(UnidadeSaude.nome_unidade).all()

    for nome, valor in gastos_contratinhos:
        if nome:
            gastos[nome] = gastos.get(nome, 0) + (valor or 0)

    # Consulta para Empenhos
    gastos_empenhos = db.session.query(
        UnidadeSaude.nome_unidade,
        func.sum(ConsumoItemEmpenho.valor_total_consumido_item)
    ).join(Empenho, Empenho.unidade_saude_id == UnidadeSaude.id)\
     .join(ConsumoItemEmpenho, ConsumoItemEmpenho.empenho_id == Empenho.id)\
     .group_by(UnidadeSaude.nome_unidade).all()

    for nome, valor in gastos_empenhos:
        if nome:
            gastos[nome] = gastos.get(nome, 0) + (valor or 0)

    # Ordenar por valor (do maior para o menor)
    sorted_gastos = sorted(gastos.items(), key=lambda item: item[1], reverse=True)
    
    labels = [item[0] for item in sorted_gastos]
    data = [item[1] for item in sorted_gastos]

    return jsonify({'labels': labels, 'data': data})

# --- ROTAS PARA RELATÓRIOS PDF ---
@app.route('/relatorio/atas/todas')
@login_required
def relatorio_lista_atas_pdf():
    todas_as_atas = Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()).all()
    if not todas_as_atas:
        flash('Nenhuma ata encontrada para gerar o relatório.', 'warning')
        return redirect(url_for('index')) 
    return reports.gerar_pdf_lista_atas(todas_as_atas)

# --- NOVA ROTA PARA RELATÓRIO DE PROCESSOS ---
@app.route('/relatorio/processos/todos')
@login_required
def relatorio_lista_processos_pdf():
    todos_os_processos = Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()
    if not todos_os_processos:
        flash('Nenhum processo encontrado para gerar o relatório.', 'warning')
        return redirect(url_for('listar_processos'))
    return reports.gerar_pdf_lista_processos(todos_os_processos)

@app.route('/relatorio/ata/<int:ata_id>/detalhes')
@login_required
def relatorio_detalhes_ata_pdf(ata_id):
    ata = Ata.query.get_or_404(ata_id)
    return reports.gerar_pdf_detalhes_ata(ata, ata.itens_ata)

@app.route('/relatorio/contrato/<int:contrato_id>/pdf')
@login_required
def relatorio_detalhes_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    return reports.gerar_pdf_detalhes_contrato(contrato)

@app.route('/relatorio/contratinho/<int:contratinho_id>/pdf')
@login_required
def relatorio_detalhes_contratinho(contratinho_id):
    contratinho = Contratinho.query.get_or_404(contratinho_id)
    return reports.gerar_pdf_detalhes_contratinho(contratinho)

@app.route('/relatorio/empenho/<int:empenho_id>/pdf')
@login_required
def relatorio_detalhes_empenho(empenho_id):
    empenho = Empenho.query.get_or_404(empenho_id)
    return reports.gerar_pdf_detalhes_empenho(empenho)

@app.route('/relatorio/consumo_unidade', methods=['GET', 'POST'])
@login_required
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
        else:
            return reports.gerar_pdf_consumo_por_unidade(unidade, dados_para_relatorio, data_inicio, data_fim)
    return render_template('selecionar_relatorio_consumo_unidade.html', form=form, titulo_pagina="Relatório de Consumo por Unidade")

@app.route('/relatorio/consumo_item', methods=['GET', 'POST'])
@login_required
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
        else:
            return reports.gerar_pdf_consumo_por_item(item_selecionado, dados_agregados_para_pdf, data_inicio, data_fim)
    return render_template('selecionar_relatorio_consumo_item.html', form=form, titulo_pagina="Relatório de Consumo por Item")

@app.route('/relatorios/contratos_vigentes_por_unidade', methods=['GET', 'POST'])
@login_required
def relatorio_contratos_vigentes_unidade():
    form = RelatorioContratosVigentesUnidadeForm()
    if form.validate_on_submit():
        unidade_id = form.unidade_saude_id.data
        unidade = db.session.get(UnidadeSaude, unidade_id)
        if not unidade:
            flash('Unidade de Saúde não encontrada.', 'danger')
            return redirect(url_for('relatorio_contratos_vigentes_unidade'))
        hoje = datetime.now(timezone.utc).date()
        contratos_vigentes = Contrato.query.filter(
            Contrato.unidade_saude_id == unidade_id,
            or_(Contrato.data_fim_vigencia >= hoje, Contrato.data_fim_vigencia == None)
        ).order_by(Contrato.data_fim_vigencia).all()
        contratinhos_vigentes = Contratinho.query.filter(
            Contratinho.unidade_saude_id == unidade_id,
            or_(Contratinho.data_fim_vigencia >= hoje, Contratinho.data_fim_vigencia == None)
        ).order_by(Contratinho.data_fim_vigencia).all()
        empenhos_vinculados = Empenho.query.filter_by(unidade_saude_id=unidade_id).order_by(Empenho.data_emissao.desc()).all()
        if not contratos_vigentes and not contratinhos_vigentes and not empenhos_vinculados:
            flash(f"Nenhum documento encontrado para a unidade '{unidade.nome_unidade}'.", 'info')
        else:
            return reports.gerar_pdf_contratos_vigentes_unidade(unidade, contratos_vigentes, contratinhos_vigentes, empenhos_vinculados)
    return render_template('selecionar_relatorio_contratos_vigentes_unidade.html', form=form, titulo_pagina="Relatório de Contratos Vigentes por Unidade")

@app.route('/relatorio/potencial_solicitacao', methods=['GET', 'POST'])
@login_required
def relatorio_potencial_de_solicitacao():
    form = RelatorioPotencialDeSolicitacaoForm()
    if form.validate_on_submit():
        unidade_id = form.unidade_saude_id.data
        unidade = db.session.get(UnidadeSaude, unidade_id)
        if not unidade:
            flash('Unidade de Saúde não encontrada.', 'danger')
            return redirect(url_for('relatorio_potencial_de_solicitacao'))

        hoje = datetime.now(timezone.utc).date()
        
        cotas_disponiveis = CotaUnidadeItem.query.join(ItemAta).join(Ata).filter(
            CotaUnidadeItem.unidade_saude_id == unidade_id,
            CotaUnidadeItem.quantidade_prevista > CotaUnidadeItem.quantidade_consumida,
            or_(Ata.data_validade >= hoje, Ata.data_validade == None)
        ).order_by(Ata.numero_ata, ItemAta.descricao_item).all()

        if not cotas_disponiveis:
            flash(f"Nenhum item com saldo de cota disponível para solicitação na unidade '{unidade.nome_unidade}' em atas vigentes.", 'info')
        else:
            return reports.gerar_pdf_potencial_solicitacao(unidade, cotas_disponiveis)
    return render_template('selecionar_relatorio_potencial.html', form=form, titulo_pagina="Relatório de Potencial de Solicitação")

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    is_debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=is_debug_mode)
