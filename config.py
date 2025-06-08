# Início do arquivo completo: config.py

import os

# Determina o diretório base do projeto
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Classe de configuração base."""
    # Chave secreta para proteger sessões e outros dados.
    # É FUNDAMENTAL que este valor seja alterado em produção para algo
    # longo, aleatório e secreto.
    # Você pode gerar uma chave segura executando no terminal:
    # python -c 'import secrets; print(secrets.token_hex(16))'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua-chave-secreta-padrao-para-desenvolvimento'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações de Alertas do Dashboard
    PERCENTUAL_SALDO_BAIXO = int(os.environ.get('PERCENTUAL_SALDO_BAIXO', 20))
    DIAS_ALERTA_PRAZO = int(os.environ.get('DIAS_ALERTA_PRAZO', 30))
    
    # Configuração do Banco de Dados
    # A variável de ambiente DATABASE_URL tem prioridade (usado em produção, ex: Heroku/Render).
    # Se não existir, usa um banco de dados SQLite local.
    DATABASE_URL_ENV = os.environ.get('DATABASE_URL')
    if DATABASE_URL_ENV and DATABASE_URL_ENV.startswith("postgres://"):
        # Garante a compatibilidade do dialeto do SQLAlchemy com a URI do Heroku
        SQLALCHEMY_DATABASE_URI = DATABASE_URL_ENV.replace("postgres://", "postgresql://", 1)
        if '?sslmode=' not in SQLALCHEMY_DATABASE_URI and not SQLALCHEMY_DATABASE_URI.endswith('?sslmode=require'):
            SQLALCHEMY_DATABASE_URI += '?sslmode=require'
        elif '?sslmode=' in SQLALCHEMY_DATABASE_URI and not SQLALCHEMY_DATABASE_URI.endswith('sslmode=require'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.split('?sslmode=')[0] + '?sslmode=require'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'saude_contratos.db')

# Fim do arquivo completo: config.py