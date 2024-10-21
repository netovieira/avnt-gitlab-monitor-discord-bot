import discord
from discord.ext import commands
from discord import app_commands
import random
from Config import Config
from user_link import UserLink
from helpers.messages import WELCOME_MESSAGES
from helpers.utils import create_text_channel_options

class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        self.user_link = UserLink(config=self.config)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.start_registration(member)

    async def start_registration(self, member):
        await member.send("Bem-vindo ao servidor, pequeno bit perdido! Eu sou o Gino, o assistente mais inteligente (e modesto) deste lado do ciberespaço. Vamos começar seu processo de registro antes que você se torne obsoleto!")
        await self.ask_role(member)

    async def ask_role(self, member):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Desenvolve algo?", custom_id="DESENVOLVEDOR"))
        view.add_item(discord.ui.Button(label="É do Administrativo?", custom_id="ADMINISTRATIVO"))
        view.add_item(discord.ui.Button(label="Ou apenas um Analista?", custom_id="ANALISTA"))
        view.add_item(discord.ui.Button(label="Faz testes então?", custom_id="TESTER"))
        view.add_item(discord.ui.Button(label="Desisto, pelo menos é da area de TI né?", custom_id="TI"))
        view.add_item(discord.ui.Button(label="Não? Não é da area de ti?", custom_id="NTI"))

        msg = await member.send("O que você faz na Moura? Escolha sabiamente, o destino do universo digital pode depender disso!", view=view)

        async def button_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                return

            role = interaction.data['custom_id']
            await msg.delete()
            if role == "TI" or role == "NTI":
                await self.ask_custom_role(member)
            else:
                await self.process_role(member, role)

        view.on_timeout = lambda: msg.delete()
        for item in view.children:
            item.callback = button_callback

    async def ask_custom_role(self, member):
        await member.send("Ah, um rebelde! Digite seu cargo então, ainda não consigo prever as coisas...")
        await member.send("Tente não quebrar meus circuitos com sua criatividade.")
        
        def check(m):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        msg = await self.bot.wait_for('message', check=check)
        await self.process_role(member, msg.content)

    async def process_role(self, member, role):
        guild = member.guild
        existing_role = discord.utils.get(guild.roles, name=role)
        if not existing_role:
            developer_role = discord.utils.get(guild.roles, name="DEVELOPERS")
            new_role = await guild.create_role(name=role, permissions=developer_role.permissions)
            await member.add_roles(new_role)
            await member.send(f"Parabéns, criei um novo cargo só para você: {role}. Sinta-se especial, mas não muito.")
        else:
            await member.add_roles(existing_role)
            await member.send(f"Você agora tem o cargo de {role}. Use-o com sabedoria, ou pelo menos tente não quebrar nada.")

        if role.lower() == "desenvolvedor":
            await self.ask_gitlab_email(member)
        else:
            await self.ask_channels(member)

    async def ask_gitlab_email(self, member):
        await member.send("Agora, ó grande desenvolvedor, forneça seu email de acesso ao GitLab Moura. E por favor, use um @jnmoura.com.br, a menos que queira me ver chorar lágrimas de código binário.")

        def check(m):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        while True:
            msg = await self.bot.wait_for('message', check=check)
            email = msg.content.strip()

            if email.lower().endswith("@jnmoura.com.br"):
                await self.user_link.link_user(member.id, email)
                await member.send("Email registrado com sucesso! Agora você está oficialmente na matriz. Não deixe o agente Smith te pegar.")
                break
            else:
                await member.send("Esse email não parece ser da Moura. Tente novamente, e dessa vez, tente não me desapontar.")

        await self.ask_channels(member)

    async def ask_channels(self, member):
        guild = member.guild
        options = await create_text_channel_options(guild)

        class ChannelSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="Escolha seus domínios digitais", options=options, max_values=len(options))
                self.selected_channels = []

            async def callback(self, interaction: discord.Interaction):
                self.selected_channels = self.values
                await interaction.response.defer()

        class ChannelView(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.select = ChannelSelect()
                self.add_item(self.select)

            @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green, custom_id="confirm", row=1)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != member.id:
                    return
                await interaction.response.defer()
                await self.process_channels(member, self.select.selected_channels)
                await interaction.message.delete()

        view = ChannelView()
        view.process_channels = self.process_channels  # Add the process_channels method to the view

        await member.send("Selecione os canais de texto que você deseja receber notificações. Escolha com sabedoria, jovem padawan do código:", view=view)

    async def process_channels(self, member, selected_channels):
        guild = member.guild
        channels_to_add = set()

        for channel_id in selected_channels:
            if channel_id.startswith('category_'):
                category_id = int(channel_id.split('_')[1])
                category = guild.get_channel(category_id)
                if category:
                    channels_to_add.update(channel.id for channel in category.channels if isinstance(channel, discord.TextChannel))
            else:
                channels_to_add.add(int(channel_id))

        for channel_id in channels_to_add:
            channel = guild.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                await channel.set_permissions(member, read_messages=True, send_messages=True)
                await member.send(f"Você agora tem acesso ao canal {channel.name}. Use-o com sabedoria, ou pelo menos tente não inundar com memes.")

        # Liberar acesso aos canais de voz
        for channel in guild.voice_channels:
            await channel.set_permissions(member, connect=True, speak=True)

        await member.send("Você também tem acesso aos canais de voz. Tente não assustar ninguém com sua voz melodiosa... ou falta dela.")
        await self.finish_registration(member)

    async def finish_registration(self, member):
        guild = member.guild
        general_channel = discord.utils.get(guild.text_channels, name="geral")
        if general_channel:
            welcome_message = random.choice(WELCOME_MESSAGES).format(member=member.mention)
            await general_channel.send(welcome_message)

        await member.send("Registro concluído, nova entidade digital! Bem-vindo ao nosso reino de zeros e uns. Que seus commits sejam sempre perfeitos e seus bugs, inexistentes (como se isso fosse possível, ha!).")

async def setup(bot):
    await bot.add_cog(Registration(bot))