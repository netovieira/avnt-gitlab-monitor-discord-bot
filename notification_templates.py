from helpers.datetime import format_date
from helpers.gitlab import translate_merge_status


def get_notification_message(event_type, action, **kwargs):
    templates = {
        'merge_request': {
            'opened': 
                "📣 Novo merge request aberto por **{author}**:\n"
                "De: `{source}` para `{target}`\n\n"
                "**Título**: {title}\n"
                "**Descrição**: {description}\n\n"
                "**Status**: {merge_status}\n"
                "**Criado em**: {created_at}\n"
                "**Última edição**: {last_edited_at}{mentions}",
            'closed': 
                "🚫 Merge request fechado: **{title}**\n"
                "Status: **{merge_status}**\n"
                "Última edição: {last_edited_at}{mentions}",
            'merged': 
                "✅ Merge request mesclado: **{title}**\n"
                "De: `{source}` para `{target}`{mentions}",
            'approved': 
                "👍 Merge request aprovado: **{title}**\n"
                "Status: **{merge_status}**{mentions}",
            'unapproved': 
                "👎 Aprovação do merge request removida: **{title}**\n"
                "Status: **{merge_status}**{mentions}",
        },
    }

    try:
        template = templates[event_type][action]
        
        # Format all date fields (ending with _at)
        for key, value in kwargs.items():
            if key.endswith('_at'):
                kwargs[key] = format_date(value)
        
        if 'merge_status' in kwargs:
            kwargs['merge_status'] = translate_merge_status(kwargs['merge_status'])
            

        if not 'mentions' in kwargs:
            kwargs['mentions'] = ""
        else:
            kwargs['mentions'] = "\n" + kwargs['mentions']

        return template.format(**kwargs)
    except KeyError as e:
        print(f"Template KeyError: {e}")
        return f"Ocorreu um erro: template ausente para {event_type} - {action}"

def get_error_message(error_type):
    error_templates = {
        'permission_denied': "⚠️ Erro: O bot não tem permissões suficientes para realizar esta ação.",
        'channel_limit': "⚠️ Erro: Limite de canais atingido para esta categoria. Por favor, arquive ou exclua canais não utilizados.",
        'user_not_found': "⚠️ Erro: Usuário não encontrado no servidor do Discord.",
        'gitlab_api_error': "⚠️ Erro: Falha ao comunicar com a API do GitLab. Por favor, verifique sua configuração.",
        'unknown_error': "⚠️ Ocorreu um erro inesperado. Por favor, verifique os logs do bot para mais informações.",
    }

    return error_templates.get(error_type, error_templates['unknown_error'])

def get_help_message():
    return """
    🤖 Bot do GitLab para Discord - Ajuda

    Este bot cria automaticamente canais para projetos e repositórios do GitLab e envia notificações para vários eventos do GitLab.

    Comandos disponíveis:

    !ajuda
    Mostra esta mensagem de ajuda com todos os comandos disponíveis.

    !config_gitlab <url> <token>
    Configura a URL e o token de acesso do GitLab.
    Exemplo: !config_gitlab https://gitlab.com seu_token_aqui

    !add_project <id> <nome>
    Adiciona um projeto do GitLab para monitoramento.
    Exemplo: !add_project 12345 "Meu Projeto"

    !add_role <função> <email>
    Associa uma função a um email do GitLab.
    Exemplo: !add_role desenvolvedor usuario@exemplo.com

    !add_notification <tipo_evento> <função>
    Configura notificações para uma função.
    Exemplo: !add_notification merge_request desenvolvedor

    !show_config
    Mostra a configuração atual do bot.

    Nota: Todos os comandos, exceto !ajuda, requerem permissões de administrador.
    """

# ... (rest of the file remains unchanged)

def get_success_message(action_type, **kwargs):
    success_templates = {
        'gitlab_config': "✅ Configuração do GitLab atualizada com sucesso!",
        'project_added': "✅ Projeto '{project_name}' (ID: {project_id}) adicionado com sucesso!",
        'user_linked': "✅ Conta do Discord vinculada com sucesso ao email do GitLab.",
        'user_unlinked': "✅ Conta do Discord desvinculada com sucesso do GitLab.",
        'channel_created': "✅ Novo canal criado para o repositório: **{repo_name}**",
    }

    template = success_templates.get(action_type, "✅ Ação concluída com sucesso.")
    return template.format(**kwargs) if kwargs else template

def get_config_message(gitlab_url, projects, roles, notifications):
    config_message = "Configuração atual do bot:\n\n"
    config_message += f"GitLab URL: {gitlab_url}\n\n"
    
    config_message += "Projetos:\n"
    for project_id, project_name in projects:
        config_message += f"- {project_name} (ID: {project_id})\n"
    
    config_message += "\nFunções:\n"
    for role, email in roles:
        config_message += f"- {role}: {email}\n"
    
    config_message += "\nNotificações:\n"
    for event_type, role in notifications:
        config_message += f"- {event_type}: {role}\n"

    return config_message