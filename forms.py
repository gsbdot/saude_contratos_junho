from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, IntegerField, DateField, SubmitField, FloatField as WTFormsFloatField, SelectField, BooleanField
from wtforms.fields import FieldList, FormField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError, Email
from models import Ata, ItemAta, UnidadeSaude, ItemContrato
from wtforms import Form as WTForm_Form 
from datetime import date
import math # Para math.isclose

# CLASSE PARA LIDAR COM INPUT DE MOEDA/FLOAT BRASILEIRO
class BrazilianFloatField(WTFormsFloatField):
    def process_formdata(self, valuelist):
        if valuelist:
            raw_value = str(valuelist[0]) 
            if raw_value and raw_value.strip(): # Verifica se não é string vazia ou só espaços
                # Remove pontos (separadores de milhar) e substitui vírgula decimal por ponto
                cleaned_value = raw_value.replace('.', '').replace(',', '.')
                try:
                    self.data = float(cleaned_value)
                except ValueError:
                    self.data = None 
                    raise ValueError(self.gettext('Não é um valor decimal válido.')) 
            else: 
                self.data = None # Se o campo for opcional e enviado vazio
        else: 
            self.data = None

def coerce_int_or_none(x):
    if x is None or str(x).strip() == '': return None
    try: return int(x)
    except ValueError: raise ValidationError('Valor inválido para seleção.')

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y']

class AtaForm(FlaskForm):
    numero_ata = StringField('Número da Ata', validators=[DataRequired(), Length(min=1, max=100)])
    ano = IntegerField('Ano da Ata', validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[Optional(), Length(max=500)])
    data_assinatura = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[Optional()])
    data_validade = DateField('Data de Validade', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Salvar Ata')

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
    quantidade_registrada = BrazilianFloatField('Qtd. Registrada', validators=[DataRequired(), NumberRange(min=0.000001, message="Qtd. deve ser positiva.")]) # MODIFICADO
    valor_unitario_registrado = BrazilianFloatField('Valor Unitário (R$)', validators=[Optional(), NumberRange(min=0)])
    lote = StringField('Lote', validators=[Optional(), Length(max=100)])

class AdicionarItensLoteAtaForm(FlaskForm):
    itens_ata = FieldList(FormField(ItemAtaLoteSubForm), min_entries=1, max_entries=30)
    submit = SubmitField('Adicionar Itens à Ata')

class ItemAtaForm(FlaskForm): 
    descricao_item = StringField('Descrição do Item', validators=[DataRequired(), Length(max=255)])
    tipo_item = SelectField('Tipo do Item', choices=ItemAta.TIPO_ITEM_CHOICES, validators=[DataRequired()])
    unidade_medida = StringField('Unidade de Medida', validators=[Optional(), Length(max=50)])
    quantidade_registrada = BrazilianFloatField('Qtd. Registrada na Ata', validators=[DataRequired(), NumberRange(min=0)]) # MODIFICADO
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
    quantidade = BrazilianFloatField('Quantidade', validators=[DataRequired(message="Quantidade é obrigatória."), NumberRange(min=0.000001, message="Quantidade deve ser positiva.")]) # MODIFICADO
    valor_unitario = BrazilianFloatField('Valor Unitário (R$)', validators=[DataRequired(message="Valor unitário é obrigatório."), NumberRange(min=0)]) 

class ContratoForm(FlaskForm): 
    numero_contrato = StringField('Número do Contrato', validators=[DataRequired(), Length(min=1, max=100)])
    objeto = TextAreaField('Objeto do Contrato', validators=[DataRequired(), Length(max=1000)])
    valor_global_contrato = BrazilianFloatField('Valor Global do Contrato (R$)', validators=[DataRequired(message="Valor global é obrigatório."), NumberRange(min=0.0)]) 
    fornecedor = StringField('Fornecedor', validators=[Optional(), Length(max=200)])
    data_assinatura_contrato = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[Optional()])
    data_inicio_vigencia = DateField('Início da Vigência', format=DATE_FORMATS, validators=[Optional()])
    data_fim_vigencia = DateField('Fim da Vigência', format=DATE_FORMATS, validators=[Optional()])
    itens_contratados = FieldList(FormField(ItemLivreContratoSubForm), min_entries=0, max_entries=50)
    submit = SubmitField('Salvar Contrato')

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

    def validate(self, extra_validators=None):
        initial_validation = super(ContratoForm, self).validate(extra_validators)
        if not initial_validation:
            return False

        is_valid = True
        soma_valor_itens = 0.0
        has_actual_items = False

        if self.itens_contratados.data:
            for item_data in self.itens_contratados.data:
                descricao = item_data.get('descricao', '').strip()
                quantidade_val = item_data.get('quantidade') 
                valor_unitario_val = item_data.get('valor_unitario')

                if descricao and quantidade_val is not None and valor_unitario_val is not None:
                    has_actual_items = True # Marcamos que há um item a ser considerado
                    try:
                        # Os valores já devem ser float aqui devido ao BrazilianFloatField
                        soma_valor_itens += float(quantidade_val) * float(valor_unitario_val)
                    except (TypeError, ValueError):
                        # Este item é inválido para a soma, mas o erro de campo deve ser mostrado pela validação do subform
                        pass
        
        valor_global = self.valor_global_contrato.data if self.valor_global_contrato.data is not None else 0.0
        
        if has_actual_items: # Só valida a soma se itens foram efetivamente adicionados e processados
            if not math.isclose(valor_global, soma_valor_itens, abs_tol=0.001): # Tolerância de 0.1 centavo
                msg_valor_global = f"R$ {valor_global:.2f}".replace('.', ',')
                msg_soma_itens = f"R$ {soma_valor_itens:.2f}".replace('.', ',')
                
                error_msg = (f"O Valor Global do Contrato ({msg_valor_global}) "
                             f"deve ser igual à soma dos valores dos itens ({msg_soma_itens}).")
                self.valor_global_contrato.errors.append(error_msg)
                is_valid = False
        
        return is_valid

class ConsumoItemSubFormulario(WTForm_Form): 
    item_ata_id = SelectField('Item da Ata', coerce=coerce_int_or_none, validators=[DataRequired(message="Item é obrigatório.")])
    quantidade_consumida = BrazilianFloatField('Quantidade Consumida', validators=[DataRequired(message="Qtd. é obrigatória."), NumberRange(min=0.000001, message="Qtd. deve ser positiva.")]) # MODIFICADO

class ContratinhoForm(FlaskForm):
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