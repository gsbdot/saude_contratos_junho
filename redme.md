# Sistema de Gestão de Contratos (SGC) - Saúde

## 1. Visão Geral

O SGC-Saúde é uma aplicação web desenvolvida em Python com o framework Flask, projetada para ser uma base de código aberto para a gestão de Atas de Registro de Preço, Contratos, Empenhos e o consumo de itens/serviços vinculados. [cite_start]O projeto inclui um sistema de cotas por unidade de saúde para controle detalhado dos gastos. 

[cite_start]A aplicação segue um modelo de negócio "Open Core", onde este sistema ("Core") é a base de código aberto, com planos de desenvolvimento de módulos "Premium" para funcionalidades ERP mais avançadas. 

## 2. Funcionalidades Implementadas

O SGC "Core" possui as seguintes funcionalidades implementadas e testadas:

* [cite_start]**CRUDs Completos:** Gerenciamento total (Criar, Ler, Atualizar, Excluir) para Atas, Itens de Atas, Contratos, Aditivos, Contratinhos, Empenhos, Unidades de Saúde e Usuários. 
* [cite_start]**Autenticação e Permissões (RBAC):** Sistema de login seguro com 3 perfis de acesso (admin, gestor, leitura), com permissões devidamente aplicadas no frontend e backend. 
* [cite_start]**Sistema de Cotas:** Lógica funcional que controla o consumo de itens por unidade, impedindo gastos que excedam o saldo da cota ou o saldo global do item. 
* **Logs e Comentários:**
    * [cite_start]Registro de auditoria para todas as ações críticas do sistema. 
    * [cite_start]Sistema de "post-its" (comentários) polimórfico para anexar notas a qualquer documento principal (Atas, Contratos, etc.). 
* **Dashboard Avançado:**
    * [cite_start]Contadores quantitativos para as principais entidades do sistema. 
    * [cite_start]Gráfico de gastos consolidados por unidade de saúde. 
    * [cite_start]Feed de atividades recentes com os últimos comentários. 
    * [cite_start]Alertas configuráveis para saldos de itens baixos e prazos de vencimento. 
* [cite_start]**Relatórios em PDF:** Geração de relatórios para listagens e detalhamento individual de Atas, Contratos, Contratinhos e Empenhos, além de relatórios de consumo e potencial de solicitação. 
* [cite_start]**Importação via CSV:** Funcionalidade para importar Atas e seus respectivos itens em lote a partir de um arquivo CSV. 

## 3. Tecnologias Utilizadas

* **Backend:** Flask
* [cite_start]**Banco de Dados:** SQLite (desenvolvimento), preparado para PostgreSQL (produção) 
* [cite_start]**ORM:** Flask-SQLAlchemy, com migrações gerenciadas pelo Flask-Migrate 
* [cite_start]**Autenticação:** Flask-Login 
* [cite_start]**Formulários:** Flask-WTF 
* [cite_start]**Frontend:** Bootstrap 5, Font Awesome 
* [cite_start]**Gráficos:** Chart.js 
* [cite_start]**Geração de PDF:** ReportLab 

## 4. Pré-requisitos

* [cite_start]Python (versão 3.10.12 ou compatível) 
* Pip (gerenciador de pacotes do Python)

## 5. Instalação e Configuração

Siga os passos abaixo para configurar o ambiente de desenvolvimento local.

**1. Clone o Repositório**
```bash
git clone <url-do-seu-repositorio>
cd <nome-da-pasta-do-projeto>