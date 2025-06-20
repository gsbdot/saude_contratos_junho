# Início do arquivo completo: models.py

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, inspect
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

def get_current_time_utc():
    return datetime.now(timezone.utc)

# --- NOVO MODELO DE PROCESSO ---
class Processo(db.Model):
    __tablename__ = 'processo'
    id = db.Column(db.Integer, primary_key=True)
    numero_processo = db.Column(db.String(100), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)

    # Relacionamentos com os outros documentos
    atas = db.relationship('Ata', back_populates='processo', lazy='dynamic')
    contratos = db.relationship('Contrato', back_populates='processo', lazy='dynamic')
    contratinhos = db.relationship('Contratinho', back_populates='processo', lazy='dynamic')
    empenhos = db.relationship('Empenho', back_populates='processo', lazy='dynamic')

    # Garante que a combinação de número e ano do processo seja única
    __table_args__ = (UniqueConstraint('numero_processo', 'ano', name='_processo_numero_ano_uc'),)

    def __repr__(self):
        return f'<Processo {self.numero_processo}/{self.ano}>'


# --- NOVO MIXIN PARA COMENTÁRIOS ---
# Esta classe auxiliar nos permite adicionar a funcionalidade de comentários
# a qualquer outro modelo de forma fácil e sem repetir código.
class Commentable:
    @property
    def comments(self):
        # Encontra todos os comentários onde o tipo e o id correspondem a este objeto.
        return Comentario.query.filter_by(
            commentable_type=self.__class__.__name__,
            commentable_id=self.id
        ).order_by(Comentario.timestamp.asc())

# === MODELO DE USUÁRIO ===
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='leitura') 
    
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id'), nullable=True)
    
    logs = db.relationship('Log', backref='user', lazy='dynamic')
    comentarios = db.relationship('Comentario', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Ata(db.Model, Commentable): # Adicionado 'Commentable'
    __tablename__ = 'ata'
    id = db.Column(db.Integer, primary_key=True)
    numero_ata = db.Column(db.String(100), unique=True, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data_assinatura = db.Column(db.DateTime, nullable=True)
    data_validade = db.Column(db.DateTime, nullable=True) 
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    
    # --- CAMPO ADICIONADO ---
    processo_id = db.Column(db.Integer, db.ForeignKey('processo.id'), nullable=True)
    processo = db.relationship('Processo', back_populates='atas')
    
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
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', name='fk_itemata_ata_id'), nullable=False)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    consumos_contratinho_itens = db.relationship('ConsumoItemContratinho', backref='item_ata_consumido', lazy='dynamic', cascade="all, delete-orphan")
    consumos_empenho_itens = db.relationship('ConsumoItemEmpenho', backref='item_ata_consumido', lazy='dynamic', cascade="all, delete-orphan")
    cotas = db.relationship('CotaUnidadeItem', backref='item_ata', lazy='dynamic', cascade="all, delete-orphan")
    def __repr__(self):
        return f'<ItemAta id={self.id} desc={self.descricao_item} saldo={self.saldo_disponivel}>'

class Contrato(db.Model, Commentable): # Adicionado 'Commentable'
    __tablename__ = 'contrato'
    id = db.Column(db.Integer, primary_key=True)
    numero_contrato = db.Column(db.String(100), unique=True, nullable=False)
    objeto = db.Column(db.Text, nullable=False)
    valor_global_contrato = db.Column(db.Float, nullable=False, default=0.0)
    fornecedor = db.Column(db.String(200), nullable=True)
    data_assinatura_contrato = db.Column(db.DateTime, nullable=True)
    data_inicio_vigencia = db.Column(db.DateTime, nullable=True)
    data_fim_vigencia_original = db.Column(db.DateTime, nullable=True)
    data_fim_vigencia = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    
    # --- CAMPO ADICIONADO ---
    processo_id = db.Column(db.Integer, db.ForeignKey('processo.id'), nullable=True)
    processo = db.relationship('Processo', back_populates='contratos')
    
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id', name='fk_contrato_unidade_saude_id'), nullable=True)
    itens_do_contrato = db.relationship('ItemContrato', backref='contrato_pai', lazy='dynamic', cascade="all, delete-orphan")
    aditivos = db.relationship('Aditivo', backref='contrato_pai', lazy='dynamic', cascade="all, delete-orphan", order_by="Aditivo.data_assinatura")
    def __repr__(self):
        return f'<Contrato {self.numero_contrato}>'

class Aditivo(db.Model, Commentable): # MODIFICADO: Adicionado ', Commentable'
    __tablename__ = 'aditivo'
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contrato.id', name='fk_aditivo_contrato_id', ondelete='CASCADE'), nullable=False)
    numero_aditivo = db.Column(db.String(100), nullable=False)
    data_assinatura = db.Column(db.DateTime, nullable=False)
    objeto = db.Column(db.Text, nullable=True)
    valor_acrescimo = db.Column(db.Float, nullable=True, default=0.0)
    prazo_adicional_dias = db.Column(db.Integer, nullable=True, default=0)
    nova_data_fim_vigencia = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    def __repr__(self):
        return f'<Aditivo {self.numero_aditivo} para Contrato ID {self.contrato_id}>'

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
    contratos_vinculados = db.relationship('Contrato', backref='unidade_saude_responsavel', lazy='dynamic', foreign_keys='Contrato.unidade_saude_id')
    cotas_itens = db.relationship('CotaUnidadeItem', backref='unidade_saude', lazy='dynamic', cascade="all, delete-orphan")
    usuarios = db.relationship('User', backref='unidade_saude', lazy='dynamic')
    def __repr__(self):
        return f'<UnidadeSaude {self.nome_unidade}>'

class CotaUnidadeItem(db.Model):
    __tablename__ = 'cota_unidade_item'
    id = db.Column(db.Integer, primary_key=True)
    item_ata_id = db.Column(db.Integer, db.ForeignKey('item_ata.id', name='fk_cota_item_ata_id', ondelete='CASCADE'), nullable=False)
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id', name='fk_cota_unidade_saude_id', ondelete='CASCADE'), nullable=False)
    quantidade_prevista = db.Column(db.Float, nullable=False, default=0.0)
    quantidade_consumida = db.Column(db.Float, nullable=False, default=0.0)
    __table_args__ = (UniqueConstraint('item_ata_id', 'unidade_saude_id', name='_item_unidade_uc'),)
    def __repr__(self):
        return f'<Cota Unidade ID {self.unidade_saude_id} para Item ID {self.item_ata_id}: {self.quantidade_prevista}>'

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

class Contratinho(db.Model, Commentable): # Adicionado 'Commentable'
    __tablename__ = 'contratinho'
    id = db.Column(db.Integer, primary_key=True)
    numero_contratinho = db.Column(db.String(100), nullable=False) 
    objeto = db.Column(db.Text, nullable=True) 
    data_emissao = db.Column(db.DateTime, nullable=False)
    data_fim_vigencia = db.Column(db.DateTime, nullable=True)
    favorecido = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    
    # --- CAMPO ADICIONADO ---
    processo_id = db.Column(db.Integer, db.ForeignKey('processo.id'), nullable=True)
    processo = db.relationship('Processo', back_populates='contratinhos')
    
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', name='fk_contratinho_ata_id'), nullable=False)
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id', name='fk_contratinho_unidade_saude_id'), nullable=True)
    valor_total_itens = db.Column(db.Float, nullable=True, default=0.0)
    valor_total_manual = db.Column(db.Float, nullable=True) 
    itens_consumidos = db.relationship('ConsumoItemContratinho', backref='contratinho_pai', lazy='dynamic', cascade="all, delete-orphan")
    def __repr__(self):
        return f'<Contratinho {self.numero_contratinho}>'

class Empenho(db.Model, Commentable): # Adicionado 'Commentable'
    __tablename__ = 'empenho'
    id = db.Column(db.Integer, primary_key=True)
    numero_empenho = db.Column(db.String(100), nullable=False) 
    descricao_simples = db.Column(db.Text, nullable=True)
    data_emissao = db.Column(db.DateTime, nullable=False)
    favorecido = db.Column(db.String(200), nullable=True)
    criado_em = db.Column(db.DateTime, default=get_current_time_utc)
    
    # --- CAMPO ADICIONADO ---
    processo_id = db.Column(db.Integer, db.ForeignKey('processo.id'), nullable=True)
    processo = db.relationship('Processo', back_populates='empenhos')
    
    ata_id = db.Column(db.Integer, db.ForeignKey('ata.id', name='fk_empenho_ata_id'), nullable=False)
    unidade_saude_id = db.Column(db.Integer, db.ForeignKey('unidade_saude.id', name='fk_empenho_unidade_saude_id'), nullable=True)
    valor_total_itens = db.Column(db.Float, nullable=True, default=0.0)
    valor_total_manual = db.Column(db.Float, nullable=True)
    itens_consumidos = db.relationship('ConsumoItemEmpenho', backref='empenho_pai', lazy='dynamic', cascade="all, delete-orphan")
    def __repr__(self):
        return f'<Empenho {self.numero_empenho}>'

class Log(db.Model):
    __tablename__ = 'log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True) 

    def __repr__(self):
        return f'<Log {self.timestamp} - {self.user.username} - {self.action}>'

# --- NOVO MODELO DE COMENTÁRIO ---
class Comentario(db.Model):
    __tablename__ = 'comentario'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Colunas para a relação polimórfica
    commentable_id = db.Column(db.Integer, nullable=False)
    commentable_type = db.Column(db.String(50), nullable=False)

    __mapper_args__ = {
        'polymorphic_on': commentable_type
    }

    def __repr__(self):
        return f'<Comentario {self.id} por {self.author.username}>'

# Fim do arquivo completo: models.py