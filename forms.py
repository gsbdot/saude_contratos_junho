# Início do arquivo completo: forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DateField, SubmitField, FloatField as WTFormsFloatField, SelectField, BooleanField, HiddenField, PasswordField
from wtforms.fields import FieldList, FormField, FileField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError, Email, EqualTo
# O modelo Processo já estava importado
from models import Ata, ItemAta, UnidadeSaude, ItemContrato, User, Processo
from wtforms import Form as WTForm_Form 
from datetime import date
import math

class ProcessoForm(FlaskForm):
    numero_processo = StringField('Número do Processo', validators=[DataRequired(), Length(max=100)])
    ano = IntegerField('Ano do Processo', validators=[DataRequired()])
    descricao = TextAreaField('Descrição/Objeto do Processo', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Salvar Processo')

class BrazilianFloatField(WTFormsFloatField):
    def process_formdata(self, valuelist):
        if valuelist:
            raw_value = str(valuelist[0]) 
            if raw_value and raw_value.strip():
                cleaned_value = raw_value.replace('.', '').replace(',', '.')
                try:
                    self.data = float(cleaned_value)
                except ValueError:
                    self.data = None 
                    raise ValueError(self.gettext('Não é um valor decimal válido.')) 
            else: 
                self.data = None
        else: 
            self.data = None

def coerce_int_or_none(x):
    if x is None or str(x).strip() == '': return None
    try: return int(x)
    except ValueError: raise ValidationError('Valor inválido para seleção.')

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y']

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class AtaForm(FlaskForm):
    # --- CAMPO ADICIONADO ---
    processo_id = SelectField('Processo Vinculado (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    numero_ata = StringField('Número da Ata', validators=[DataRequired(), Length(min=1, max=100)])
    ano = IntegerField('Ano da Ata', validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    data_assinatura = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[Optional()])
    data_validade = DateField('Data de Validade', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Salvar Ata')
    
    # --- MÉTODO __init__ ADICIONADO ---
    def __init__(self, *args, **kwargs):
        super(AtaForm, self).__init__(*args, **kwargs)
        self.processo_id.choices = [('', '--- Sem Processo Vinculado ---')] + \
                                   [(p.id, f"{p.numero_processo}/{p.ano}") for p in Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()]

    def validate_data_assinatura(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Assinatura não pode ser no futuro.')

    def validate_data_validade(self, field):
        if field.data and self.data_assinatura.data:
            if field.data < self.data_assinatura.data:
                raise ValidationError('A Data de Validade não pode ser anterior à Data de Assinatura.')

class ItemAtaLoteSubForm(WTForm_Form):
    descricao_item = StringField('Descrição do Item', validators=[DataRequired(), Length(max=255)])
    tipo_item = SelectField('Tipo do Item', choices=ItemAta.TIPO_ITEM_CHOICES, validators=[DataRequired()])
    unidade_medida = StringField('Unidade de Medida', validators=[Optional(), Length(max=50)])
    quantidade_registrada = BrazilianFloatField('Qtd. Registrada', validators=[DataRequired(), NumberRange(min=0.000001, message="Qtd. deve ser positiva.")])
    valor_unitario_registrado = BrazilianFloatField('Valor Unitário (R$)', validators=[Optional(), NumberRange(min=0)])
    lote = StringField('Lote', validators=[Optional(), Length(max=100)])

class AdicionarItensLoteAtaForm(FlaskForm):
    itens_ata = FieldList(FormField(ItemAtaLoteSubForm), min_entries=1, max_entries=30)
    submit = SubmitField('Adicionar Itens à Ata')

class ItemAtaForm(FlaskForm): 
    descricao_item = StringField('Descrição do Item', validators=[DataRequired(), Length(max=255)])
    tipo_item = SelectField('Tipo do Item', choices=ItemAta.TIPO_ITEM_CHOICES, validators=[DataRequired()])
    unidade_medida = StringField('Unidade de Medida', validators=[Optional(), Length(max=50)])
    quantidade_registrada = BrazilianFloatField('Qtd. Registrada na Ata', validators=[DataRequired(), NumberRange(min=0)])
    valor_unitario_registrado = BrazilianFloatField('Valor Unitário (R$)', validators=[Optional(), NumberRange(min=0)])
    lote = StringField('Lote', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Salvar Item da Ata')

class UnidadeSaudeForm(FlaskForm):
    nome_unidade = StringField('Nome da Unidade', validators=[DataRequired(), Length(max=150)])
    tipo_unidade = SelectField('Tipo da Unidade', choices=UnidadeSaude.TIPO_UNIDADE_CHOICES, validators=[DataRequired(message="Selecione um tipo válido.")])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    email_responsavel = StringField('Email do Responsável', validators=[Optional(), Email(message="Email inválido."), Length(max=120)])
    submit = SubmitField('Salvar Unidade de Saúde')
    def validate_tipo_unidade(self, field):
        if field.data == '': raise ValidationError('Selecione um tipo de unidade válido.')

class ItemLivreContratoSubForm(WTForm_Form):
    descricao = StringField('Descrição do Item', validators=[DataRequired(message="Descrição do item é obrigatória."), Length(max=500)])
    unidade_medida = StringField('Unidade', validators=[Optional(), Length(max=50)])
    quantidade = BrazilianFloatField('Quantidade', validators=[DataRequired(message="Quantidade é obrigatória."), NumberRange(min=0.000001, message="Quantidade deve ser positiva.")])
    valor_unitario = BrazilianFloatField('Valor Unitário (R$)', validators=[DataRequired(message="Valor unitário é obrigatório."), NumberRange(min=0)]) 

class ContratoForm(FlaskForm):
    # --- CAMPO ADICIONADO ---
    processo_id = SelectField('Processo Vinculado (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    numero_contrato = StringField('Número do Contrato', validators=[DataRequired(), Length(min=1, max=100)])
    objeto = TextAreaField('Objeto do Contrato', validators=[DataRequired(), Length(max=1000)])
    unidade_saude_id = SelectField('Unidade de Saúde Responsável (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    fornecedor = StringField('Fornecedor', validators=[Optional(), Length(max=200)])
    data_assinatura_contrato = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[Optional()])
    data_inicio_vigencia = DateField('Início da Vigência', format=DATE_FORMATS, validators=[Optional()])
    data_fim_vigencia = DateField('Fim da Vigência', format=DATE_FORMATS, validators=[Optional()])
    itens_contratados = FieldList(FormField(ItemLivreContratoSubForm), min_entries=1, max_entries=50)
    submit = SubmitField('Salvar Contrato')

    def __init__(self, *args, **kwargs):
        super(ContratoForm, self).__init__(*args, **kwargs)
        self.unidade_saude_id.choices = [('', '--- Nenhuma (Geral da Secretaria) ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]
        # --- LINHA ADICIONADA ---
        self.processo_id.choices = [('', '--- Sem Processo Vinculado ---')] + \
                                   [(p.id, f"{p.numero_processo}/{p.ano}") for p in Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()]

    def validate_data_assinatura_contrato(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Assinatura não pode ser no futuro.')

    def validate_data_inicio_vigencia(self, field):
        if field.data and self.data_assinatura_contrato.data:
            if field.data < self.data_assinatura_contrato.data:
                raise ValidationError('O Início da Vigência não pode ser anterior à Data de Assinatura.')
    
    def validate_data_fim_vigencia(self, field):
        if field.data and self.data_inicio_vigencia.data:
            if field.data < self.data_inicio_vigencia.data:
                raise ValidationError('O Fim da Vigência não pode ser anterior ao Início da Vigência.')
        if field.data and self.data_assinatura_contrato.data: 
            if field.data < self.data_assinatura_contrato.data:
                raise ValidationError('O Fim da Vigência não pode ser anterior à Data de Assinatura.')

class AditivoForm(FlaskForm):
    numero_aditivo = StringField('Número do Termo Aditivo', validators=[DataRequired(), Length(max=100)])
    data_assinatura = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[DataRequired()])
    objeto = TextAreaField('Objeto do Aditivo', validators=[Optional(), Length(max=1000)])
    valor_acrescimo = BrazilianFloatField('Acréscimo de Valor (R$)', validators=[Optional()], 
                                          description="Use valor negativo para decréscimo. Ex: -500,00")
    prazo_adicional_dias = IntegerField('Prazo Adicional (dias)', validators=[Optional()],
                                        description="Use valor negativo para redução de prazo.")
    nova_data_fim_vigencia = DateField('Ou Nova Data Final de Vigência', format=DATE_FORMATS, validators=[Optional()],
                                       description="Preencha para definir uma data final exata, ignorando o prazo em dias.")
    submit = SubmitField('Salvar Termo Aditivo')

class ConsumoItemSubFormulario(WTForm_Form): 
    item_ata_id = SelectField('Item da Ata', coerce=coerce_int_or_none, validators=[DataRequired(message="Item é obrigatório.")])
    quantidade_consumida = BrazilianFloatField('Quantidade Consumida', validators=[DataRequired(message="Qtd. é obrigatória."), NumberRange(min=0.000001, message="Qtd. deve ser positiva.")])

class ContratinhoForm(FlaskForm):
    # --- CAMPO ADICIONADO ---
    processo_id = SelectField('Processo Vinculado (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    numero_contratinho = StringField('Número do Contratinho/Doc.', validators=[DataRequired(), Length(max=100)])
    objeto = TextAreaField('Objeto Geral (Opcional se itens detalham)', validators=[Optional(), Length(max=1000)])
    favorecido = StringField('Favorecido/Fornecedor', validators=[Optional(), Length(max=200)])
    data_emissao = DateField('Data de Emissão', format=DATE_FORMATS, validators=[DataRequired()])
    data_fim_vigencia = DateField('Data Fim de Vigência (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    ata_id = SelectField('Ata Vinculada (Obrigatório)', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione uma Ata para carregar itens.")])
    unidade_saude_id = SelectField('Unidade de Saúde Destino (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    valor_total_manual = BrazilianFloatField('Valor Total Manual (Opcional)', validators=[Optional(), NumberRange(min=0)])
    itens_consumidos = FieldList(FormField(ConsumoItemSubFormulario), min_entries=1, max_entries=20) 
    submit = SubmitField('Salvar Contratinho')

    def validate_data_emissao(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Emissão não pode ser no futuro.')

    def validate_data_fim_vigencia(self, field):
        if field.data and self.data_emissao.data:
            if field.data < self.data_emissao.data:
                raise ValidationError('A Data Fim de Vigência não pode ser anterior à Data de Emissão.')

    def __init__(self, *args, **kwargs):
        super(ContratinhoForm, self).__init__(*args, **kwargs)
        self.ata_id.choices = [('', '--- Selecione uma Ata ---')] + \
                              [(ata.id, f"{ata.numero_ata}/{ata.ano}") for ata in Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()).all()]
        self.unidade_saude_id.choices = [('', '--- Nenhuma Unidade ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]
        # --- LINHA ADICIONADA ---
        self.processo_id.choices = [('', '--- Sem Processo Vinculado ---')] + \
                                   [(p.id, f"{p.numero_processo}/{p.ano}") for p in Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()]
        
        ata_selecionada_id = None
        if self.ata_id.data is not None: 
            try: ata_selecionada_id = int(self.ata_id.data)
            except ValueError: pass
        elif kwargs.get('obj') and hasattr(kwargs['obj'], 'ata_id') and kwargs['obj'].ata_id is not None:
            ata_selecionada_id = kwargs['obj'].ata_id
        item_choices_options = [('', '--- Selecione uma Ata Principal Primeiro ---')]
        if ata_selecionada_id is not None:
            itens_da_ata_selecionada = ItemAta.query.filter_by(ata_id=ata_selecionada_id).filter(ItemAta.saldo_disponivel > 0).order_by(ItemAta.descricao_item).all()
            if itens_da_ata_selecionada:
                item_choices_options = [('', '--- Selecione um Item ---')] + \
                                   [(item.id, f"{item.descricao_item} (Saldo: {item.saldo_disponivel:.2f} {item.unidade_medida or ''}, VU: R${item.valor_unitario_registrado:.2f})")
                                    for item in itens_da_ata_selecionada]
            else:
                if ItemAta.query.filter_by(ata_id=ata_selecionada_id).first():
                    item_choices_options = [('', 'Todos os itens desta Ata estão com saldo zero')]
                else:
                    item_choices_options = [('', 'Nenhum item cadastrado para esta Ata')]
        for item_form_field_entry in self.itens_consumidos:
            if hasattr(item_form_field_entry, 'form') and hasattr(item_form_field_entry.form, 'item_ata_id'):
                item_form_field_entry.form.item_ata_id.choices = item_choices_options

class EmpenhoForm(FlaskForm):
    # --- CAMPO ADICIONADO ---
    processo_id = SelectField('Processo Vinculado (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    numero_empenho = StringField('Número do Empenho', validators=[DataRequired(), Length(max=100)])
    descricao_simples = TextAreaField('Descrição Simplificada (Opcional se itens detalham)', validators=[Optional(), Length(max=1000)])
    favorecido = StringField('Favorecido', validators=[Optional(), Length(max=200)])
    data_emissao = DateField('Data de Emissão', format=DATE_FORMATS, validators=[DataRequired()])
    ata_id = SelectField('Ata Vinculada (Obrigatório)', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione uma Ata para carregar itens.")])
    unidade_saude_id = SelectField('Unidade de Saúde Destino (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    valor_total_manual = BrazilianFloatField('Valor Total Manual (Opcional)', validators=[Optional(), NumberRange(min=0)])
    itens_consumidos = FieldList(FormField(ConsumoItemSubFormulario), min_entries=1, max_entries=20)
    submit = SubmitField('Salvar Empenho')

    def validate_data_emissao(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Emissão não pode ser no futuro.')

    def __init__(self, *args, **kwargs):
        super(EmpenhoForm, self).__init__(*args, **kwargs)
        self.ata_id.choices = [('', '--- Selecione uma Ata ---')] + \
                              [(ata.id, f"{ata.numero_ata}/{ata.ano}") for ata in Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()).all()]
        self.unidade_saude_id.choices = [('', '--- Nenhuma Unidade ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]
        # --- LINHA ADICIONADA ---
        self.processo_id.choices = [('', '--- Sem Processo Vinculado ---')] + \
                                   [(p.id, f"{p.numero_processo}/{p.ano}") for p in Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()]
                                   
        ata_selecionada_id = None
        if self.ata_id.data is not None:
            try: ata_selecionada_id = int(self.ata_id.data)
            except ValueError: pass
        elif kwargs.get('obj') and hasattr(kwargs['obj'], 'ata_id') and kwargs['obj'].ata_id is not None:
            ata_selecionada_id = kwargs['obj'].ata_id
        item_choices_options = [('', '--- Selecione uma Ata Principal Primeiro ---')]
        if ata_selecionada_id is not None:
            itens_da_ata_selecionada = ItemAta.query.filter_by(ata_id=ata_selecionada_id).filter(ItemAta.saldo_disponivel > 0).order_by(ItemAta.descricao_item).all()
            if itens_da_ata_selecionada:
                item_choices_options = [('', '--- Selecione um Item ---')] + \
                                   [(item.id, f"{item.descricao_item} (Saldo: {item.saldo_disponivel:.2f} {item.unidade_medida or ''}, VU: R${item.valor_unitario_registrado:.2f})")
                                    for item in itens_da_ata_selecionada]
            else:
                if ItemAta.query.filter_by(ata_id=ata_selecionada_id).first():
                    item_choices_options = [('', 'Todos os itens desta Ata estão com saldo zero')]
                else:
                    item_choices_options = [('', 'Nenhum item cadastrado para esta Ata')]
        for item_form_field_entry in self.itens_consumidos:
            if hasattr(item_form_field_entry, 'form') and hasattr(item_form_field_entry.form, 'item_ata_id'):
                item_form_field_entry.form.item_ata_id.choices = item_choices_options

class RelatorioContratosVigentesUnidadeForm(FlaskForm):
    unidade_saude_id = SelectField('Unidade de Saúde', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione uma Unidade de Saúde.")])
    submit = SubmitField('Gerar Relatório')

    def __init__(self, *args, **kwargs):
        super(RelatorioContratosVigentesUnidadeForm, self).__init__(*args, **kwargs)
        self.unidade_saude_id.choices = [('', '--- Selecione uma Unidade ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]

class RelatorioConsumoUnidadeForm(FlaskForm):
    unidade_saude_id = SelectField('Unidade de Saúde', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione uma Unidade de Saúde.")])
    data_inicio = DateField('Data Início (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    data_fim = DateField('Data Fim (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Gerar Relatório')

    def __init__(self, *args, **kwargs):
        super(RelatorioConsumoUnidadeForm, self).__init__(*args, **kwargs)
        self.unidade_saude_id.choices = [('', '--- Selecione uma Unidade ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]

    def validate_data_inicio(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Início não pode ser no futuro.')

    def validate_data_fim(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Fim não pode ser no futuro.')
        if field.data and self.data_inicio.data:
            if field.data < self.data_inicio.data:
                raise ValidationError('A Data de Fim não pode ser anterior à Data de Início.')

class RelatorioConsumoPorItemForm(FlaskForm):
    item_ata_id = SelectField('Item da Ata Específico', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione um Item da Ata.")])
    data_inicio = DateField('Data Início do Consumo (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    data_fim = DateField('Data Fim do Consumo (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Gerar Relatório de Consumo do Item')

    def __init__(self, *args, **kwargs):
        super(RelatorioConsumoPorItemForm, self).__init__(*args, **kwargs)
        todos_os_itens_ata = ItemAta.query.join(Ata, ItemAta.ata_id == Ata.id)\
                                        .order_by(Ata.ano.desc(), Ata.numero_ata.desc(), ItemAta.descricao_item).all()
        self.item_ata_id.choices = [('', '--- Selecione um Item ---')] + \
                                   [(item.id, f"{item.descricao_item} (Ata: {item.ata_mae.numero_ata}/{item.ata_mae.ano}, Saldo: {item.saldo_disponivel:.0f})")
                                    for item in todos_os_itens_ata]

    def validate_data_inicio(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Início não pode ser no futuro.')

    def validate_data_fim(self, field):
        if field.data and field.data > date.today():
            raise ValidationError('A Data de Fim não pode ser no futuro.')
        if field.data and self.data_inicio.data:
            if field.data < self.data_inicio.data:
                raise ValidationError('A Data de Fim não pode ser anterior à Data de Início.')

class ImportCSVForm(FlaskForm):
    csv_file = FileField('Arquivo CSV', validators=[DataRequired(message="Por favor, selecione um arquivo.")])
    submit = SubmitField('Importar')

class CotaUnidadeSubForm(WTForm_Form):
    unidade_saude_id = HiddenField()
    quantidade_prevista = BrazilianFloatField('Cota', validators=[Optional(), NumberRange(min=0)])

class GerenciarCotasForm(FlaskForm):
    cotas = FieldList(FormField(CotaUnidadeSubForm))
    submit = SubmitField('Salvar Cotas')

class RelatorioPotencialDeSolicitacaoForm(FlaskForm):
    unidade_saude_id = SelectField('Unidade de Saúde', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione uma Unidade de Saúde.")])
    submit = SubmitField('Gerar Relatório')

    def __init__(self, *args, **kwargs):
        super(RelatorioPotencialDeSolicitacaoForm, self).__init__(*args, **kwargs)
        self.unidade_saude_id.choices = [('', '--- Selecione uma Unidade ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]

class UserCreationForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    role = SelectField('Nível de Acesso (Role)', choices=[('admin', 'Administrador'), ('gestor', 'Gestor de Unidade'), ('leitura', 'Apenas Leitura')], validators=[DataRequired()])
    unidade_saude_id = SelectField('Vincular à Unidade de Saúde (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    submit = SubmitField('Criar Usuário')

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.unidade_saude_id.choices = [('', '--- Nenhuma ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

class UserEditForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Nova Senha (Opcional)', validators=[Optional(), Length(min=6, message='A senha deve ter no mínimo 6 caracteres.')])
    password2 = PasswordField('Confirmar Nova Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    role = SelectField('Nível de Acesso (Role)', choices=[('admin', 'Administrador'), ('gestor', 'Gestor de Unidade'), ('leitura', 'Apenas Leitura')], validators=[DataRequired()])
    unidade_saude_id = SelectField('Vincular à Unidade de Saúde (Opcional)', coerce=coerce_int_or_none, validators=[Optional()])
    submit = SubmitField('Salvar Alterações')

    def __init__(self, original_username, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.unidade_saude_id.choices = [('', '--- Nenhuma ---')] + \
                                        [(u.id, u.nome_unidade) for u in UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade).all()]

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

class CommentForm(FlaskForm):
    content = TextAreaField('Comentário', validators=[DataRequired(), Length(min=1, max=1000)])
    submit = SubmitField('Enviar Comentário')

# Fim do arquivo: forms.py