document.addEventListener('DOMContentLoaded', function() {
    const formContratinho = document.getElementById('formContratinho');
    const formEmpenho = document.getElementById('formEmpenho'); // Adicione id="formEmpenho" ao seu form de empenho
    const formContratoClassico = document.getElementById('formContratoClassico');

    // Variáveis comuns
    let itensConsumidosContainer, addItemBtn, itemTemplateDiv, fieldListName, itemBlocoClass, removeBtnClass;
    let itemIndex = 0; // Será inicializado corretamente dentro de cada bloco if

    // --- LÓGICA PARA CONTRATINHOS (E EMPENHOS - a ser adaptada) ---
    if (formContratinho || formEmpenho) {
        let selectAtaPrincipalId;
        let descricaoAtaDivId, textoDescricaoAtaId, itemAtaSelectClass;

        if (formContratinho) {
            selectAtaPrincipalId = 'selectAtaPrincipal';
            itensConsumidosContainerId = 'itens-consumidos-container';
            addItemBtnId = 'add-item-btn';
            itemTemplateId = 'item-consumido-template';
            descricaoAtaDivId = 'descricao_ata_selecionada_div';
            textoDescricaoAtaId = 'texto_descricao_ata';
            fieldListName = 'itens_consumidos';
            itemBlocoClass = 'item-consumido-bloco';
            removeBtnClass = 'remove-item-btn'; // Classe do botão de remover para Contratinho
            itemAtaSelectClass = 'item-ata-select';
        } else if (formEmpenho) {
            // Adapte estes IDs para corresponderem aos do seu formEmpenho.html
            selectAtaPrincipalId = 'selectAtaPrincipalEmpenho'; // EX: <select id="selectAtaPrincipalEmpenho">...</select>
            itensConsumidosContainerId = 'itens-consumidos-empenho-container'; // EX: <div id="itens-consumidos-empenho-container">...</div>
            addItemBtnId = 'add-item-empenho-btn'; // EX: <button id="add-item-empenho-btn">...</button>
            itemTemplateId = 'item-empenho-template'; // EX: <div id="item-empenho-template" style="display:none;">...</div>
            descricaoAtaDivId = 'descricao_ata_empenho_div';
            textoDescricaoAtaId = 'texto_descricao_ata_empenho';
            fieldListName = 'itens_consumidos'; // Mesmo nome de FieldList no EmpenhoForm
            itemBlocoClass = 'item-empenhado-bloco'; // Classe para o bloco do item no empenho
            removeBtnClass = 'remove-item-empenho-btn'; // Classe para o botão de remover no empenho
            itemAtaSelectClass = 'item-ata-empenho-select'; // Classe para os selects de item no empenho
        }

        const selectAtaPrincipal = document.getElementById(selectAtaPrincipalId);
        itensConsumidosContainer = document.getElementById(itensConsumidosContainerId);
        addItemBtn = document.getElementById(addItemBtnId);
        itemTemplateDiv = document.getElementById(itemTemplateId);
        const descricaoAtaDiv = document.getElementById(descricaoAtaDivId);
        const textoDescricaoAta = document.getElementById(textoDescricaoAtaId);
        
        if (!selectAtaPrincipal || !itensConsumidosContainer || !addItemBtn || !itemTemplateDiv) {
            // console.warn("Elementos do formulário de Contratinho/Empenho não encontrados. JS não será ativado para esta parte.");
            // return; // Não retorna, pois pode haver lógica para outro formulário
        } else {
            itemIndex = itensConsumidosContainer.children.length;

            function carregarItensDaAta(ataId, callbackParaPopularSelects) {
                if (!ataId) {
                    document.querySelectorAll(`.${itemAtaSelectClass}`).forEach(select => {
                        select.innerHTML = '<option value="">--- Selecione uma Ata Principal Primeiro ---</option>';
                    });
                    if (descricaoAtaDiv) descricaoAtaDiv.style.display = 'none';
                    if (textoDescricaoAta) textoDescricaoAta.textContent = '';
                    return;
                }
                fetch(`/itens_da_ata_json/${ataId}`)
                    .then(response => response.ok ? response.json() : Promise.reject(response))
                    .then(data => {
                        if (data.error) {
                            console.error('Erro ao buscar itens:', data.error);
                            if (descricaoAtaDiv) descricaoAtaDiv.style.display = 'none';
                            if (textoDescricaoAta) textoDescricaoAta.textContent = '';
                            return;
                        }
                        if (data.ata_descricao && textoDescricaoAta && descricaoAtaDiv) {
                            textoDescricaoAta.textContent = data.ata_descricao;
                            descricaoAtaDiv.style.display = 'block';
                        } else if (descricaoAtaDiv) {
                            descricaoAtaDiv.style.display = 'none';
                            if (textoDescricaoAta) textoDescricaoAta.textContent = '';
                        }
                        const popularSelectsFn = selectsParaPopular => {
                            selectsParaPopular.forEach(select => {
                                const currentValue = select.value;
                                select.innerHTML = ''; 
                                data.itens.forEach(item => {
                                    const option = document.createElement('option');
                                    option.value = item.id;
                                    option.textContent = item.text;
                                    select.appendChild(option);
                                });
                                if (currentValue && Array.from(select.options).some(opt => opt.value === currentValue)) {
                                    select.value = currentValue;
                                }
                            });
                        };
                        if (callbackParaPopularSelects) { // Para um select específico (nova linha)
                            callbackParaPopularSelects(data.itens);
                        } else { // Para todos os selects existentes
                            popularSelectsFn(document.querySelectorAll(`.${itemAtaSelectClass}`));
                        }
                    })
                    .catch(error => {
                        console.error('Falha ao buscar itens da ata:', error);
                        document.querySelectorAll(`.${itemAtaSelectClass}`).forEach(select => {
                            select.innerHTML = '<option value="">Erro ao carregar itens</option>';
                        });
                        if(descricaoAtaDiv) descricaoAtaDiv.style.display = 'none';
                        if(textoDescricaoAta) textoDescricaoAta.textContent = '';
                    });
            }

            selectAtaPrincipal.addEventListener('change', function() {
                carregarItensDaAta(this.value);
            });
            if (selectAtaPrincipal.value) {
                carregarItensDaAta(selectAtaPrincipal.value);
            } else {
                 document.querySelectorAll(`.${itemAtaSelectClass}`).forEach(select => {
                    if (!select.value && (select.options.length === 0 || (select.options.length > 0 && select.options[0].value === ""))) {
                        select.innerHTML = '<option value="">--- Selecione uma Ata Principal Primeiro ---</option>';
                    }
                });
            }

            addItemBtn.addEventListener('click', function() {
                const novoItemHtml = itemTemplateDiv.innerHTML.replace(/__prefix__/g, itemIndex);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = novoItemHtml;
                const novoItemBloco = tempDiv.firstElementChild;
                const h6 = novoItemBloco.querySelector('h6');
                if (h6) h6.textContent = `Item ${itensConsumidosContainer.children.length + 1}`;
                itensConsumidosContainer.appendChild(novoItemBloco);
                const novaSelectDeItem = novoItemBloco.querySelector(`.${itemAtaSelectClass}`);
                if (novaSelectDeItem && selectAtaPrincipal && selectAtaPrincipal.value) {
                    carregarItensDaAta(selectAtaPrincipal.value, function(itensOpcoes) {
                        novaSelectDeItem.innerHTML = '';
                        itensOpcoes.forEach(item => {
                            const option = document.createElement('option');
                            option.value = item.id;
                            option.textContent = item.text;
                            novaSelectDeItem.appendChild(option);
                        });
                    });
                } else if (novaSelectDeItem) {
                    novaSelectDeItem.innerHTML = '<option value="">--- Selecione uma Ata Principal Primeiro ---</option>';
                }
                itemIndex++;
                atualizarBotoesRemoverComuns();
            });

            itensConsumidosContainer.addEventListener('click', function(e) {
                if (e.target && e.target.classList.contains(removeBtnClass)) {
                    e.target.closest(`.${itemBlocoClass}`).remove();
                    renumerarItensNosBlocosComuns();
                    atualizarBotoesRemoverComuns();
                }
            });

            function renumerarItensNosBlocosComuns() {
                const blocos = itensConsumidosContainer.querySelectorAll(`.${itemBlocoClass}`);
                blocos.forEach((bloco, idx) => {
                    const h6 = bloco.querySelector('h6');
                    if (h6) h6.textContent = `Item ${idx + 1}`;
                    bloco.querySelectorAll('input, select, textarea').forEach(input => {
                        if (input.name) input.name = input.name.replace(new RegExp(`${fieldListName}-\\d+-`), `${fieldListName}-${idx}-`);
                        if (input.id) input.id = input.id.replace(new RegExp(`${fieldListName}-\\d+-`), `${fieldListName}-${idx}-`);
                    });
                });
                itemIndex = blocos.length;
            }

            function atualizarBotoesRemoverComuns() {
                const blocos = itensConsumidosContainer.querySelectorAll(`.${itemBlocoClass}`);
                const minEntries = 1; 
                blocos.forEach((bloco, idx) => {
                    let btnRemover = bloco.querySelector(`.${removeBtnClass}`);
                    if (!btnRemover) {
                        const templateBtn = itemTemplateDiv.querySelector(`.${removeBtnClass}`);
                        if (templateBtn) {
                            btnRemover = templateBtn.cloneNode(true);
                            const headerDiv = bloco.querySelector('.d-flex.justify-content-between.align-items-center');
                            if (headerDiv && headerDiv.children.length > 0) {
                                headerDiv.appendChild(btnRemover);
                            }
                        }
                    }
                    if (btnRemover) {
                        btnRemover.style.display = (blocos.length <= minEntries) ? 'none' : 'inline-block';
                    }
                });
            }
            renumerarItensNosBlocosComuns(); 
            atualizarBotoesRemoverComuns();
        }
    }

    // --- LÓGICA PARA CONTRATOS CLÁSSICOS (ITENS LIVRES) ---
    if (formContratoClassico) {
        itensConsumidosContainerId = 'itens-contratados-container';
        addItemBtnId = 'add-item-contrato-btn';
        itemTemplateId = 'item-contrato-template';
        fieldListName = 'itens_contratados';
        itemBlocoClass = 'item-contratado-bloco'; // Usar a classe definida no template criar_contrato.html
        removeBtnClass = 'remove-item-contrato-btn'; // Usar a classe definida no template

        itensConsumidosContainer = document.getElementById(itensConsumidosContainerId);
        addItemBtn = document.getElementById(addItemBtnId);
        itemTemplateDiv = document.getElementById(itemTemplateId);

        if (!itensConsumidosContainer || !addItemBtn || !itemTemplateDiv) {
            // console.warn("Elementos do formulário de Contrato Clássico não encontrados. JS não será ativado para esta parte.");
        } else {
            itemIndex = itensConsumidosContainer.children.length;

            addItemBtn.addEventListener('click', function() {
                const novoItemHtml = itemTemplateDiv.innerHTML.replace(/__prefix__/g, itemIndex);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = novoItemHtml;
                const novoItemBloco = tempDiv.firstElementChild;

                const h6 = novoItemBloco.querySelector('h6');
                if (h6) h6.textContent = `Item ${itensConsumidosContainer.children.length + 1}`;
                
                itensConsumidosContainer.appendChild(novoItemBloco);
                itemIndex++;
                atualizarBotoesRemoverContratoClassico(); // Chama a função específica
            });

            itensConsumidosContainer.addEventListener('click', function(e) {
                if (e.target && e.target.classList.contains(removeBtnClass)) {
                    e.target.closest(`.${itemBlocoClass}`).remove();
                    renumerarItensContratoClassico(); // Chama a função específica
                    atualizarBotoesRemoverContratoClassico();
                }
            });

            function renumerarItensContratoClassico() {
                const blocos = itensConsumidosContainer.querySelectorAll(`.${itemBlocoClass}`);
                blocos.forEach((bloco, idx) => {
                    const h6 = bloco.querySelector('h6');
                    if (h6) h6.textContent = `Item ${idx + 1}`;
                    bloco.querySelectorAll('input, select, textarea').forEach(input => {
                        if (input.name) input.name = input.name.replace(new RegExp(`${fieldListName}-\\d+-`), `${fieldListName}-${idx}-`);
                        if (input.id) input.id = input.id.replace(new RegExp(`${fieldListName}-\\d+-`), `${fieldListName}-${idx}-`);
                    });
                });
                itemIndex = blocos.length;
            }

            function atualizarBotoesRemoverContratoClassico() {
                const blocos = itensConsumidosContainer.querySelectorAll(`.${itemBlocoClass}`);
                 // Para ContratoForm, min_entries é 0, então os itens são opcionais e todos podem ser removidos.
                const minEntriesContrato = 0;

                blocos.forEach((bloco) => {
                    let btnRemover = bloco.querySelector(`.${removeBtnClass}`);
                    if (!btnRemover && itemTemplateDiv) { 
                        const templateBtn = itemTemplateDiv.querySelector(`.${removeBtnClass}`);
                        if (templateBtn) {
                            btnRemover = templateBtn.cloneNode(true);
                            const headerDiv = bloco.querySelector('.d-flex.justify-content-between.align-items-center');
                            if (headerDiv && headerDiv.children.length > 0) { 
                                headerDiv.appendChild(btnRemover);
                            }
                        }
                    }
                    if (btnRemover) {
                         // Se min_entries é 0, o botão de remover deve estar sempre visível se houver algum item.
                        btnRemover.style.display = 'inline-block';
                    }
                });
                 if (blocos.length === 0 && addItemBtn) {
                    // Se não houver itens, não faz nada especial com o botão de adicionar.
                }
            }
            renumerarItensContratoClassico(); 
            atualizarBotoesRemoverContratoClassico();
        }
    }
});