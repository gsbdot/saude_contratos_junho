from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

def get_current_time_utc():
    return datetime.now(timezone.utc)

class Ata(db.Model):
    __tablename__ = 'ata'
    id = db.Column(db.Integer, primary_key=True)
    numero_ata = db.Column(db.String(100), unique=True, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data_assinatura = db.Column(db.DateTime, nullable=True)
    data_validade = db.Column(db.DateTime, nullable=True) 
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)

    contratinhos = db.relationship('Contratinho', backref='ata_vinculada', lazy=True, cascade="all, delete-orphan")
    empenhos = db.relationship('Empenho', backref='ata_vinculada', lazy=True, cascade="all, delete-orphan")
    itens_ata = db.relationship('ItemAta', backref='ata_mae', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Ata {self.numero_ata}/{self.ano}>'

class ItemAta(db.Model):
    __tablename__ = 'item_ata'
    id = db.Column(db.Integer, primary_key=True)
    descricao_item = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(50), nullable=True)
    quantidade_registrada = db.Column(db.Float, nullable=False, default=0.0)
    saldo_disponivel = db.Column(db.Float, nullable=False, default=0.0)
    valor_unitario_registrado = db.Column(db.Float, nullable=True)
    lote = db.Column(db.String(100), nullable=True)
    
    TIPO_ITEM_CHOICES = [
        ('MEDICAMENTO', 'Medicamento'), 
        ('MATERIAL_CONSUMO', 'Material de Consumo'),
        ('EQUIPAMENTO', 'Equipamento'), 
        ('SERVICO', 'Serviço'), 
        ('OUTRO', 'Outro')
    ]
    tipo_item = db.Column(db.String(50), nullable=False, default='OUTRO')
    
    # Campos REMOVIDOS:
    # data_garantia_fim = db.Column(db.DateTime, nullable=True)
    # requer_calibracao = db.Column(db.Boolean, default=False, nullable=True)
    # ultima_calibracao = db.Column(db.DateTime, nullable=True)
    # proxima_calibracao = db.Column(db.DateTime, nullable=True)
    # reutilizavel = db.Column(db.Boolean, default=False, nullable=True)

    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', name='fk_itemata_ata_id'), nullable=False)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)

    consumos_contratinho_itens = db.relationship('ConsumoItemContratinho', backref='item_ata_consumido', lazy='dynamic', cascade="all, delete-orphan")
    consumos_empenho_itens = db.relationship('ConsumoItemEmpenho', backref='item_ata_consumido', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ItemAta id={self.id} desc={self.descricao_item} saldo={self.saldo_disponivel}>'

class Contrato(db.Model): # Contrato Clássico
    __tablename__ = 'contrato'
    id = db.Column(db.Integer, primary_key=True)
    numero_contrato = db.Column(db.String(100), unique=True, nullable=False)
    objeto = db.Column(db.Text, nullable=False)
    valor_global_contrato = db.Column(db.Float, nullable=False) 
    fornecedor = db.Column(db.String(200), nullable=True)
    data_assinatura_contrato = db.Column(db.DateTime, nullable=True)
    data_inicio_vigencia = db.Column(db.DateTime, nullable=True)
    data_fim_vigencia = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    valor_total_itens = db.Column(db.Float, nullable=True, default=0.0)
    itens_do_contrato = db.relationship('ItemContrato', backref='contrato_pai', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Contrato {self.numero_contrato}>'

class UnidadeSaude(db.Model):
    __tablename__ = 'unidade_saude'
    id = db.Column(db.Integer, primary_key=True)
    nome_unidade = db.Column(db.String(150), unique=True, nullable=False)
    TIPO_UNIDADE_CHOICES = [
        ('', '-- Selecione --'),
        ('SECRETARIA', 'Secretaria (Sede)'), 
        ('HOSPITAL', 'Hospital'),
        ('UPA', 'UPA - Unidade de Pronto Atendimento'), 
        ('UBS', 'UBS - Unidade Básica de Saúde'),
        ('CAPS', 'CAPS - Centro de Atenção Psicossocial'),
        ('VIGILANCIA', 'Vigilância Sanitária/Epidemiológica'),
        ('FARMACIA', 'Farmácia Municipal/Polo'), 
        ('LABORATORIO', 'Laboratório'),
        ('OUTRO', 'Outro Tipo de Unidade')
    ]
    tipo_unidade = db.Column(db.String(50), nullable=False, default='OUTRO')
    endereco = db.Column(db.String(255), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    email_responsavel = db.Column(db.String(120), nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)

    contratinhos_vinculados = db.relationship('Contratinho', backref='unidade_saude_solicitante', lazy='dynamic', foreign_keys='Contratinho.unidade_saude_id')
    empenhos_vinculados = db.relationship('Empenho', backref='unidade_saude_solicitante', lazy='dynamic', foreign_keys='Empenho.unidade_saude_id')

    def __repr__(self):
        return f'<UnidadeSaude {self.nome_unidade}>'

class ConsumoItemContratinho(db.Model):
    __tablename__ = 'consumo_item_contratinho'
    id = db.Column(db.Integer, primary_key=True)
    contratinho_id = db.Column(db.Integer, db.ForeignKey('contratinho.id', name='fk_consumoitemcontratinho_contratinho_id', ondelete='CASCADE'), nullable=False)
    item_ata_id = db.Column(db.Integer, db.ForeignKey('item_ata.id', name='fk_consumoitemcontratinho_item_ata_id', ondelete='RESTRICT'), nullable=False)
    quantidade_consumida = db.Column(db.Float, nullable=False)
    valor_unitario_no_consumo = db.Column(db.Float, nullable=True) 
    valor_total_consumido_item = db.Column(db.Float, nullable=True) 

class ConsumoItemEmpenho(db.Model):
    __tablename__ = 'consumo_item_empenho'
    id = db.Column(db.Integer, primary_key=True)
    empenho_id = db.Column(db.Integer, db.ForeignKey('empenho.id', name='fk_consumoitemempenho_empenho_id', ondelete='CASCADE'), nullable=False)
    item_ata_id = db.Column(db.Integer, db.ForeignKey('item_ata.id', name='fk_consumoitemempenho_item_ata_id', ondelete='RESTRICT'), nullable=False)
    quantidade_consumida = db.Column(db.Float, nullable=False)
    valor_unitario_no_consumo = db.Column(db.Float, nullable=True) 
    valor_total_consumido_item = db.Column(db.Float, nullable=True) 

class ItemContrato(db.Model):
    __tablename__ = 'item_contrato' 
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id', name='fk_itemcontrato_contrato_id', ondelete='CASCADE'), nullable=False)
    descricao = db.Column(db.String(500), nullable=False)
    unidade_medida = db.Column(db.String(50), nullable=True)
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float, nullable=True) 
    valor_total_item = db.Column(db.Float, nullable=True) 

    def __repr__(self):
        return f'<ItemContrato {self.descricao[:30]} para Contrato ID {self.contrato_id}>'

class Contratinho(db.Model):
    __tablename__ = 'contratinho'
    id = db.Column(db.Integer, primary_key=True)
    numero_contratinho = db.Column(db.String(100), nullable=False) 
    objeto = db.Column(db.Text, nullable=True) 
    data_emissao = db.Column(db.DateTime, nullable=False, default=get_current_time_utc)
    data_fim_vigencia = db.Column(db.DateTime, nullable=True) 
    favorecido = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', name='fk_contratinho_ata_id'), nullable=False)
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id', name='fk_contratinho_unidade_saude_id'), nullable=True)
    
    valor_total_itens = db.Column(db.Float, nullable=True, default=0.0)
    valor_total_manual = db.Column(db.Float, nullable=True) 

    itens_consumidos = db.relationship('ConsumoItemContratinho', backref='contratinho_pai', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Contratinho {self.numero_contratinho}>'

class Empenho(db.Model):
    __tablename__ = 'empenho'
    id = db.Column(db.Integer, primary_key=True)
    numero_empenho = db.Column(db.String(100), nullable=False) 
    descricao_simples = db.Column(db.Text, nullable=True)
    data_emissao = db.Column(db.DateTime, nullable=False, default=get_current_time_utc)
    favorecido = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', name='fk_empenho_ata_id'), nullable=False)
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id', name='fk_empenho_unidade_saude_id'), nullable=True)

    valor_total_itens = db.Column(db.Float, nullable=True, default=0.0)
    valor_total_manual = db.Column(db.Float, nullable=True)

    itens_consumidos = db.relationship('ConsumoItemEmpenho', backref='empenho_pai', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Empenho {self.numero_empenho}>'