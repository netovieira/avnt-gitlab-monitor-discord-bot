import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from Config import Config
from user_link import UserLink
from helpers.messages import WELCOME_MESSAGES
from helpers.utils import create_text_channel_options
from typing import Optional, List

class ChannelSelectView(discord.ui.View):
    def __init__(self, options: List[discord.SelectOption], member: discord.Member):
        super().__init__(timeout=300)
        self.member = member
        self.selected_channels = []
        self.setup_select(options)

    def setup_select(self, options: List[discord.SelectOption]):
        select = discord.ui.Select(
            placeholder="Escolha seus canais...",
            options=options,
            max_values=len(options)
        )

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != self.member.id:
                return
            self.selected_channels = select.values
            await interaction.response.defer()

        select.callback = select_callback
        self.add_item(select)

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.member.id:
            return
        self.stop()
        await interaction.response.defer()

class RoleSelectView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=300)
        self.member = member
        self.value = None
        self.setup_role_select()

    def setup_role_select(self):
        options = [
            discord.SelectOption(label="Desenvolvedor", value="DESENVOLVEDOR", emoji="🙄", description="Para desenvolvedores"),
            discord.SelectOption(label="Administrativo", value="ADMINISTRATIVO", emoji="😉", description="Para equipe administrativa"),
            discord.SelectOption(label="Analista", value="ANALISTA", emoji="😆", description="Para analistas"),
            discord.SelectOption(label="Tester", value="TESTER", emoji="🤔", description="Para testers"),
            discord.SelectOption(label="TI Geral", value="TI", emoji="😅", description="Para outros profissionais de TI"),
            discord.SelectOption(label="Não TI", value="NTI", emoji="😵", description="Para profissionais fora da TI")
        ]
        
        select = discord.ui.Select(
            placeholder="Escolha seu cargo...",
            options=options
        )

        async def select_callback(interaction: discord.Interaction):
            if interaction.user.id != self.member.id:
                return
            self.value = select.values[0]
            self.stop()
            await interaction.response.defer()

        select.callback = select_callback
        self.add_item(select)

class CustomRoleModal(discord.ui.Modal, title="Cadastro de Cargo"):
    role = discord.ui.TextInput(
        label="Qual seu cargo?",
        placeholder="Digite seu cargo aqui...",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = str(self.role)
        self.stop()

class GitLabEmailModal(discord.ui.Modal, title="Email do GitLab"):
    email = discord.ui.TextInput(
        label="Email do GitLab",
        placeholder="seu.email@jnmoura.com.br",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.value = str(self.email)
        self.stop()

class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        self.user_link = UserLink()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.start_registration(member)

    @app_commands.command(name="register", description="Iniciar processo de registro manualmente")
    async def manual_register(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.start_registration(interaction.user)
        await interaction.followup.send("Processo de registro iniciado! Verifique suas mensagens privadas.", ephemeral=True)

    async def start_registration(self, member: discord.Member):
        try:
            await member.send(
                "Bem-vindo ao servidor, pequeno bit perdido! Eu sou o Gino, o assistente mais inteligente "
                "(e modesto) deste lado do ciberespaço. Vamos começar seu processo de registro antes que "
                "você se torne obsoleto!"
            )
            await self.ask_role(member)
        except discord.Forbidden:
            channel = await self.get_welcome_channel(member.guild)
            await channel.send(
                f"{member.mention}, não consegui te enviar mensagem privada! "
                "Por favor, habilite mensagens privadas do servidor e use /register para começar seu registro."
            )

    async def ask_role(self, member: discord.Member):
        view = RoleSelectView(member)
        msg = await member.send(
            "O que você faz na Moura? Escolha sabiamente, o destino do universo digital pode depender disso!",
            view=view
        )

        await view.wait()
        await msg.delete()

        if view.value is None:
            await member.send("Tempo esgotado! Use /register para começar novamente.")
            return

        if view.value in ["TI", "NTI"]:
            await self.ask_custom_role(member)
        else:
            await self.process_role(member, view.value)

    async def ask_custom_role(self, member: discord.Member):
        modal = CustomRoleModal()
        msg = await member.send("Ah, um rebelde! Clique abaixo para informar seu cargo:")
        
        view = discord.ui.View()
        button = discord.ui.Button(label="Informar Cargo", style=discord.ButtonStyle.primary)
        
        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                return
            await interaction.response.send_modal(modal)
            
        button.callback = button_callback
        view.add_item(button)
        
        await msg.edit(view=view)
        await modal.wait()
        
        if modal.value:
            await self.process_role(member, modal.value)
        else:
            await member.send("Tempo esgotado! Use /register para começar novamente.")

    async def process_role(self, member: discord.Member, role: str):
        guild = member.guild
        existing_role = discord.utils.get(guild.roles, name=role)
        
        try:
            if not existing_role:
                developer_role = discord.utils.get(guild.roles, name="DEVELOPERS")
                new_role = await guild.create_role(
                    name=role,
                    permissions=developer_role.permissions if developer_role else discord.Permissions.none()
                )
                await member.add_roles(new_role)
                await member.send(f"Parabéns, criei um novo cargo só para você: {role}. Sinta-se especial, mas não muito.")
            else:
                await member.add_roles(existing_role)
                await member.send(f"Você agora tem o cargo de {role}. Use-o com sabedoria, ou pelo menos tente não quebrar nada.")

            if role.upper() == "DESENVOLVEDOR":
                await self.ask_gitlab_email(member)
            else:
                await self.ask_channels(member)
                
        except discord.Forbidden:
            await member.send("Não tenho permissão para gerenciar cargos. Por favor, contate um administrador.")
        except Exception as e:
            await member.send(f"Ocorreu um erro ao atribuir seu cargo: {str(e)}")

    async def ask_gitlab_email(self, member: discord.Member):
        while True:
            modal = GitLabEmailModal()
            msg = await member.send("Agora, ó grande desenvolvedor, forneça seu email do GitLab:")
            
            view = discord.ui.View()
            button = discord.ui.Button(label="Informar Email GitLab", style=discord.ButtonStyle.primary)
            
            async def button_callback(interaction: discord.Interaction):
                if interaction.user.id != member.id:
                    return
                await interaction.response.send_modal(modal)
                
            button.callback = button_callback
            view.add_item(button)
            
            await msg.edit(view=view)
            await modal.wait()
            
            if not modal.value:
                await member.send("Tempo esgotado! Use /register para começar novamente.")
                return
                
            if modal.value.lower().endswith("@jnmoura.com.br"):
                await self.user_link.link_user(member.id, modal.value)
                await member.send(
                    "Email registrado com sucesso! Agora você está oficialmente na matriz. "
                    "Não deixe o agente Smith te pegar."
                )
                break
            else:
                await member.send(
                    "Esse email não parece ser da Moura. Tente novamente, e dessa vez, "
                    "tente não me desapontar."
                )

        await self.ask_channels(member)

    async def ask_channels(self, member: discord.Member):
        options = await create_text_channel_options(member.guild)
        view = ChannelSelectView(options, member)
        
        msg = await member.send(
            "Selecione os canais de texto que você deseja receber notificações. "
            "Escolha com sabedoria, jovem padawan do código:",
            view=view
        )

        await view.wait()
        await msg.delete()

        if view.selected_channels:
            await self.process_channels(member, view.selected_channels)
        else:
            await member.send("Nenhum canal selecionado ou tempo esgotado. Use /register para tentar novamente.")

    async def process_channels(self, member: discord.Member, selected_channels: List[str]):
        guild = member.guild
        channels_to_add = set()

        for channel_id in selected_channels:
            if channel_id.startswith('category_'):
                category_id = int(channel_id.split('_')[1])
                category = guild.get_channel(category_id)
                if category:
                    channels_to_add.update(
                        channel.id for channel in category.channels
                        if isinstance(channel, discord.TextChannel)
                    )
            else:
                channels_to_add.add(int(channel_id))

        added_channels = []
        for channel_id in channels_to_add:
            channel = guild.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    await channel.set_permissions(member, read_messages=True, send_messages=True)
                    added_channels.append(channel.name)
                except discord.Forbidden:
                    await member.send(f"Não consegui dar acesso ao canal {channel.name}. Permissões insuficientes.")

        if added_channels:
            channels_list = "\n• ".join(added_channels)
            await member.send(f"Você agora tem acesso aos seguintes canais:\n• {channels_list}")

        # Configure voice channels
        try:
            for channel in guild.voice_channels:
                await channel.set_permissions(member, connect=True, speak=True)
            await member.send("Você também tem acesso aos canais de voz. Tente não assustar ninguém com sua voz melodiosa... ou falta dela.")
        except discord.Forbidden:
            await member.send("Não consegui configurar permissões para canais de voz. Por favor, contate um administrador.")

        await self.finish_registration(member)

    async def finish_registration(self, member: discord.Member):
        guild = member.guild
        general_channel = discord.utils.get(guild.text_channels, name="geral")
        if general_channel:
            welcome_message = random.choice(WELCOME_MESSAGES).format(member=member.mention)
            await general_channel.send(welcome_message)

        await member.send(
            "Registro concluído, nova entidade digital! Bem-vindo ao nosso reino de zeros e uns. "
            "Que seus commits sejam sempre perfeitos e seus bugs, inexistentes (como se isso fosse possível, ha!)."
        )

    async def get_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get or create welcome channel"""
        channel = discord.utils.get(guild.text_channels, name="boas-vindas")
        if not channel:
            try:
                channel = await guild.create_text_channel(
                    "boas-vindas",
                    topic="Canal de boas-vindas e registro"
                )
            except discord.Forbidden:
                channel = guild.system_channel or guild.text_channels[0]
        return channel

    @app_commands.command(name="force_register", description="Força o registro de um usuário")
    @app_commands.checks.has_permissions(administrator=True)
    async def force_register(self, interaction: discord.Interaction, member: discord.Member):
        """Force start registration for a user (Admin only)"""
        await interaction.response.defer(ephemeral=True)
        await self.start_registration(member)
        await interaction.followup.send(f"Processo de registro iniciado para {member.mention}!", ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "Você não tem permissão para usar este comando.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Ocorreu um erro: {str(error)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Registration(bot))
    await bot.tree.sync()