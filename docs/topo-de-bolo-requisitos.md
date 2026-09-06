# Requisitos — Gerador de Topo de Bolo

> Documento escrito pelo Samir, versão 1.0 (MVP). Guardado aqui porque só
> existia na máquina dele. **Não editar**: é a fonte do que ele pediu, e o
> que eu decidir por cima dela fica em `plano.md`, separado.

---

MORUMBI 3D
Documento de Requisitos — Gerador de Topo de Bolo
Versão 1.0 • MVP
1. Objetivo
Criar um gerador online que permita ao cliente montar um topo de bolo personalizado a partir de modelos paramétricos pré-definidos, visualizar o resultado e gerar um arquivo 3D adequado para impressão, preferencialmente STL e/ou 3MF.
2. Proposta de valor
Personalização simples e visual.
Prévia antes da compra.
Redução do trabalho manual da Morumbi 3D.
Produtos padronizados e reproduzíveis.
Centenas de combinações usando poucos modelos-base.
3. Fluxo principal do usuário
Etapa
Ação
1
Escolher categoria/estilo
2
Escolher modelo
3
Informar nome
4
Informar idade/número
5
Adicionar frase opcional
6
Escolher tamanho
7
Escolher cores
8
Visualizar em 3D
9
Validar texto automaticamente
10
Gerar arquivo
11
Exibir preço
12
Enviar pedido/arquivo para a Morumbi 3D
4. Funcionalidades do MVP
Recurso
Requisito
Modelos
Biblioteca de templates paramétricos.
Texto
Nome, idade, número, frase curta e ano.
Fontes
Fontes previamente testadas para impressão 3D.
Tamanho
Presets como 12, 15, 18 e 20 cm.
Cores
Seleção de cores por peça/camada.
Prévia 3D
Visualização antes da geração.
Validação
Limite de caracteres e compatibilidade.
Geração
STL/3MF conforme template.
Nomenclatura
SKU + dados principais do pedido.
Pedido
WhatsApp, orçamento ou checkout.
5. Campos de personalização
Nome obrigatório, com limite configurável.
Idade/número opcional.
Frase opcional com limite de caracteres.
Data/ano opcional.
Tema e estilo.
Formato do topo.
Base/haste padronizada.
Tamanho por presets; tamanho livre em fase futura.
6. Requisitos técnicos de impressão
O gerador deve usar modelos paramétricos preparados para FDM.
Texto deve ser convertido em geometria antes da exportação.
Definir espessura mínima para elementos.
Evitar detalhes excessivamente finos e partes sem conexão.
Conexões entre letras, decoração e haste devem ser estruturalmente seguras.
O modelo deve manter proporções ao mudar de tamanho.
Deve existir área segura para nomes longos.
Todo template deve ser testado fisicamente antes de venda.
7. Sistema de templates
A primeira versão não precisa gerar qualquer desenho do zero. Cada produto será um template paramétrico aprovado pela Morumbi 3D.
Campo
Exemplo
Obrigatório
SKU
M3D-TB-001
Sim
Modelo
Arco Floral
Sim
Categoria
Casamento
Sim
Campos
Nome + data
Sim
Tamanho
12–25 cm
Sim
Fontes
Lobster / Montserrat
Sim
Cores
Até 3
Não
Licença
Próprio/comercial
Sim
8. Categorias iniciais
Aniversário infantil
Aniversário adulto
Casamento
Noivado
Chá revelação
Bodas
Batizado
Formatura
Corporativo
Datas comemorativas
9. Produtos iniciais sugeridos
Nome + idade
Nome + número grande
Parabéns + nome
Feliz Aniversário + nome
Nome em arco
Nome + coração
Nome + estrela
Nome + flores
Nome + coroa
Nome + composição infantil abstrata
10. Qualidade e validação
Bloquear configurações frágeis.
Alertar nomes longos.
Impedir exportação de geometria inválida.
Validar malha antes do download.
Manter espessuras e conexões dentro dos parâmetros definidos.
Separar templates em teste dos modelos publicados.
11. Arquivo gerado
Padrão sugerido:
M3D-TB-001_MARIA_5_18CM.3mf
STL pode ser disponibilizado quando o modelo não exigir informações adicionais de impressão.
12. Painel administrativo
Cadastrar e editar templates.
Ativar/desativar modelos.
Cadastrar fontes autorizadas.
Definir limites de texto.
Definir tamanhos e cores.
Definir preço.
Visualizar configurações geradas.
Baixar arquivos.
Acompanhar gerações e pedidos.
13. Monetização
Prévia gratuita + venda do produto físico.
Venda do STL/3MF quando a licença permitir.
Personalização premium.
Topos prontos para retirada.
Combos com Morumbi Festas.
Kits: topo + nome + idade + decoração de mesa.
14. Integração com Morumbi Festas
O gerador deve funcionar como ferramenta comercial. Depois de escolher o topo, o cliente poderá receber sugestões de letreiro de mesa, painel, kit Pegue e Monte, nome personalizado e outros produtos da Morumbi 3D.
15. Experiência do usuário
Interface mobile-first.
Poucos campos por etapa.
Prévia atualizada imediatamente.
Botão principal: GERAR MEU TOPO.
Mostrar tamanho aproximado.
Mostrar preço antes da finalização.
Compartilhamento por WhatsApp.
16. Critérios de aceite do MVP
Cliente consegue criar sem intervenção manual.
Arquivo abre corretamente no Bambu Studio.
Modelo fatia sem erros.
Texto permanece legível após impressão.
Topo é fisicamente resistente dentro dos parâmetros definidos.
Cliente consegue revisar antes de gerar.
Configuração fica registrada.
Arquivo recebe nomenclatura padronizada.
Mínimo de 10 templates testados no lançamento.
17. Fases de desenvolvimento
Fase
Escopo
Resultado
1
10 modelos + nome + idade + tamanho + prévia
MVP
2
Fontes, cores, frases e categorias
Catálogo ampliado
3
Pagamento + pedido + WhatsApp
Venda automatizada
4
Gerador de kits e combinações
Ecossistema Morumbi 3D
5
Parametrização avançada
Plataforma de produtos
18. Propriedade intelectual
Registrar a origem de cada template. Priorizar modelos criados pela Morumbi 3D ou arquivos cuja licença permita explicitamente uso comercial e venda de produtos físicos. Personagens, marcas, escudos, logos e outros elementos protegidos devem ser tratados separadamente.
19. Backlog inicial
Definir identidade visual.
Selecionar 10 templates.
Definir dimensões e espessuras.
Selecionar fontes testadas.
Definir sistema de haste.
Criar regras para nomes curtos/longos.
Criar protótipo da interface.
Implementar visualização 3D.
Implementar geração de geometria.
Testar STL/3MF no Bambu Studio.
Imprimir os 10 modelos.
Ajustar modelos.
Cadastrar preços.
Publicar MVP.
20. Visão futura
O Gerador de Topo de Bolo deve ser o primeiro módulo de uma plataforma maior: o cliente informa a ocasião, escolhe um estilo e a Morumbi 3D gera uma família coerente de produtos — topo de bolo, letreiro de mesa, placa, lembrancinha, chaveiro, display e outros.
