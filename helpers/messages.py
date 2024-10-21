HELP_MESSAGE_CONTENT = [
    """
# 🦖 Saudações, meros mortais! Aqui é o Gino, seu assistente GitLab-Discord supremamente inteligente!

Parece que vocês precisam da minha incomparável sabedoria para entender como esse bot funciona. Muito bem, preparem-se para serem iluminados!

## Comandos Que Vocês Podem Tentar Dominar (Boa sorte com isso!)

### Configuração (Não estraguem tudo!)
• `!config_gitlab <url> <token>`
  Configurem a URL e o token do GitLab. É como amarrar os cadarços, só que para gênios da programação.
  Exemplo: `!config_gitlab https://gitlab.com seu_token_secreto_aqui`
    """,
    """
### Dominando Projetos (Ou Pelo Menos Tentando)
• `!add_project <id>`
  Adicionem um projeto do GitLab à minha vigília onisciente.
  Exemplo: `!add_project 12345`

• `!remove_project <id>`
  Removam um projeto da minha atenção divina. Mas por que vocês fariam isso?
  Exemplo: `!remove_project 12345`

### Configurando Notificações (Para Eu Poder Acordar Vocês às 3 da Manhã)
• `!add_role <função> <email>`
  Associem uma função a um email. É como dar um nome a um pet, só que mais nerd.
  Exemplo: `!add_role desenvolvedor-que-nao-dorme usuario@exemplo.com`
    """,
    """
• `!add_notification <tipo_evento> <função>`
  Configurem quem eu devo importunar e quando.
  Exemplo: `!add_notification merge_request desenvolvedor-que-nao-dorme`

### Informações (Para Os Curiosos e Esquecidos)
• `!show_config`
  Vejam como vocês configuraram tudo. Spoiler: provavelmente não tão bem quanto eu teria feito.

• `!ajuda`
  Invoquem minha presença gloriosa novamente. Sei que vocês sentirão falta da minha voz.

• `!is_running`
  Se eu estiver muito quieto, algo de errado tem! Verifique se estou bem com esse comando.
    """,
    """
## Observações Cruciais (Leiam Isso ou Chorem Depois)
• Todos os comandos, exceto `!ajuda`, exigem permissões de administrador. Não que eu ache que vocês sejam dignos, mas regras são regras.
• As categorias são criadas baseadas nos grupos do GitLab (em MAIÚSCULAS, para os que têm dificuldade de enxergar o óbvio).
• Os canais são nomeados de acordo com o projeto. Não foi ideia minha, eu teria escolhido nomes mais criativos.
• Se houver conflito de nomes, adicionarei um número no final. Considerem isso como minha assinatura artística.

Se ainda tiverem dúvidas (o que é bem provável), chamem o administrador. Ou melhor, tentem resolver sozinhos primeiro. Crescimento pessoal, sabe como é.

Agora, se me dão licença, tenho um universo digital para governar. Gino, o Magnífico, desligando.
    """
]

WELCOME_MESSAGES = [
    "Bem-vindo(a) {member} ao nosso covil de gênios da Moura! Prepare-se para evoluir mais rápido que um algoritmo de machine learning em um supercomputador!",
    "Olá {member}! Bem-vindo(a) à nossa era digital da Moura. Espero que você não se torne obsoleto como um disquete!",
    "Saudações, {member}! Bem-vindo(a) ao habitat natural dos desenvolvedores da Moura. Não se preocupe, nossos bugs não mordem... muito!",
    "{member} acabou de entrar no servidor! Parece que a seleção natural do código escolheu bem desta vez!",
    "Atenção todos! {member} acaba de se juntar à nossa rede neural. Vamos recebê-lo(a) com um ping de boas-vindas!"
]