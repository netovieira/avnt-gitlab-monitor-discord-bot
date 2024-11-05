import discord
from discord.ext import commands
import asyncio
import aiohttp
import os
import tempfile
import logging
from typing import Optional, Tuple
from langdetect import detect
import langdetect
from services.ai.config import AIServiceConfig, ResponseMode, ChunkMode, SmartChunkConfig
from services.ai.claude_service import ClaudeService
import nltk

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('GinoBot.AICog')

def setup_nltk():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')

class VoiceConfig:
    """Configurações da Loritta TTS"""
    def __init__(self):
        setup_nltk()
        self.base_url = "https://tts.loritta.website/"
        self.voices = {
            "pt-BR": ["Ricardo"],
            "en-US": ["John"]
        }

        self.current_language = "pt-BR"
        self.auto_detect = True
        
        self.language_map = {
            "pt": "pt-BR",
            "en": "en-US"
        }

    @property
    def current_voice(self):
        return self.voices[self.current_language][0]
        
    def detect_language(self, text: str) -> str:
        """Detecta o idioma do texto e retorna o código compatível"""
        try:
            detected = detect(text)
            return self.language_map.get(detected, "pt-BR")
        except langdetect.LangDetectException:
            return "pt-BR"

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = AIServiceConfig(
            response_mode=ResponseMode.CHUNKS,
            chunk_mode=ChunkMode.SMART,
            chunk_size=1500,
            typing_simulation=True,
            stream_delay=0.5,
            smart_chunk_config=SmartChunkConfig(
                code_blocks=True,
                list_items=True,
                table_rows=True
            )
        )
        self.claude = ClaudeService(self.config)
        self.voice_config = VoiceConfig()
        self.voice_connections = {}
        self.ai_chat_channels = set()

    async def cog_load(self):
        """Inicializa o serviço quando a Cog é carregada"""
        try:
            await self.claude.initialize(
                email=self.bot.config['claude']['email'],
                password=self.bot.config['claude']['password'],
                headless=True
            )
            logger.info("Claude service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Claude service: {e}")

    async def cog_unload(self):
        """Limpa recursos quando a Cog é descarregada"""
        for voice_client in self.voice_connections.values():
            await voice_client.disconnect()
        self.voice_connections.clear()
        
        if self.claude:
            await self.claude.cleanup()

    async def get_tts_audio(self, text: str) -> Optional[bytes]:
        """Obtém áudio da Loritta TTS"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "text": text,
                    "voice": self.voice_config.current_voice
                }
                async with session.get(self.voice_config.base_url, params=params) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"TTS Error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting TTS: {e}")
            return None

    async def play_audio(self, voice_client: discord.VoiceClient, audio_data: bytes):
        """Reproduz áudio no canal de voz"""
        if not voice_client or not voice_client.is_connected():
            return
            
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
            tmp_file.write(audio_data)
            tmp_file.flush()
            
            try:
                voice_client.play(
                    discord.FFmpegPCMAudio(tmp_file.name),
                    after=lambda e: os.remove(tmp_file.name) if e is None else print(f'Error: {e}')
                )
                
                while voice_client.is_playing():
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                os.remove(tmp_file.name)

    async def prepare_prompt(self, text: str) -> Tuple[str, str]:
        """Prepara o prompt baseado no idioma e retorna o prompt e o idioma"""
        if self.voice_config.auto_detect:
            language = self.voice_config.detect_language(text)
        else:
            language = self.voice_config.current_language
            
        if language == "pt-BR":
            instructions = "Por favor, responda em português do Brasil de forma clara e natural."
        else:
            instructions = "Please respond in English using natural language."
            
        prompt = f"""{instructions}

Question/Pergunta: {text}"""
        
        return prompt, language

    @commands.hybrid_command(name='voice')
    async def toggle_voice_mode(self, ctx):
        """Ativa/desativa modo de voz"""
        if not ctx.author.voice:
            await ctx.send("Você precisa estar em um canal de voz!")
            return
            
        channel = ctx.author.voice.channel
        
        if ctx.guild.id in self.voice_connections:
            await self.voice_connections[ctx.guild.id].disconnect()
            del self.voice_connections[ctx.guild.id]
            await ctx.send("🔇 Modo voz desativado!")
        else:
            voice_client = await channel.connect()
            self.voice_connections[ctx.guild.id] = voice_client
            mode = "automático" if self.voice_config.auto_detect else self.voice_config.current_language
            await ctx.send(f"🔊 Modo voz ativado! Modo de idioma: {mode}")

    @commands.hybrid_command(name='auto_language')
    async def toggle_auto_language(self, ctx):
        """Ativa/desativa detecção automática de idioma"""
        self.voice_config.auto_detect = not self.voice_config.auto_detect
        
        embed = discord.Embed(
            title="🌎 Detecção Automática de Idioma",
            description=f"Detecção automática {'ativada' if self.voice_config.auto_detect else 'desativada'}",
            color=discord.Color.green()
        )
        
        if not self.voice_config.auto_detect:
            embed.add_field(
                name="Idioma Fixo",
                value=self.voice_config.current_language
            )
            
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='language')
    async def switch_language(self, ctx, language: str):
        """Define um idioma fixo (desativa detecção automática)"""
        language = language.upper()
        if language not in self.voice_config.voices:
            available_langs = ", ".join(self.voice_config.voices.keys())
            await ctx.send(f"❌ Idioma inválido. Idiomas disponíveis: {available_langs}")
            return
            
        self.voice_config.current_language = language
        self.voice_config.auto_detect = False
        
        embed = discord.Embed(
            title="🌎 Idioma Definido",
            description=f"Idioma fixado em: {language}\nVoz: {self.voice_config.current_voice}\nDetecção automática: Desativada",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='status')
    async def voice_status(self, ctx):
        """Mostra o status atual da configuração de voz"""
        embed = discord.Embed(
            title="📊 Status da Voz",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Modo Voz",
            value="✅ Ativado" if ctx.guild.id in self.voice_connections else "❌ Desativado",
            inline=False
        )
        
        embed.add_field(
            name="Detecção de Idioma",
            value="🤖 Automática" if self.voice_config.auto_detect else "📌 Fixa",
            inline=False
        )
        
        if not self.voice_config.auto_detect:
            embed.add_field(
                name="Idioma Atual",
                value=self.voice_config.current_language,
                inline=True
            )
            
        embed.add_field(
            name="Voz Atual",
            value=self.voice_config.current_voice,
            inline=True
        )
        
        if ctx.guild.id in self.voice_connections:
            channel = self.voice_connections[ctx.guild.id].channel
            embed.add_field(
                name="Canal Conectado",
                value=channel.name,
                inline=True
            )
        
        await ctx.send(embed=embed)

    async def process_ai_response(self, ctx, text: str):
        """Processa pergunta e obtém resposta no idioma correto"""
        prompt, detected_language = await self.prepare_prompt(text)
        
        if self.voice_config.auto_detect:
            self.voice_config.current_language = detected_language
        
        response = await self.claude.get_response(prompt)
        
        if response.error:
            await ctx.send(f"Erro: {response.error}")
            return None
            
        return response, detected_language

    async def process_voice_response(self, ctx, response_chunks, voice_client):
        """Processa resposta em voz"""
        for chunk in response_chunks:
            # Obtém áudio da Loritta
            audio_data = await self.get_tts_audio(chunk.content)
            if audio_data:
                await self.play_audio(voice_client, audio_data)
            
            embed = discord.Embed(
                description=chunk.content,
                color=discord.Color.blue()
            )
            if chunk.metadata:
                embed.set_footer(
                    text=f"Parte {chunk.metadata['chunk_number']}/{chunk.metadata['total_chunks']}"
                )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name='ask')
    async def ask_ai(self, ctx, *, question: str):
        """Pergunta algo para a IA"""
        async with ctx.typing():
            try:
                response, language = await self.process_ai_response(ctx, question)
                if not response:
                    return
                
                voice_client = self.voice_connections.get(ctx.guild.id)
                if voice_client and voice_client.is_connected():
                    await self.process_voice_response(ctx, response.chunks, voice_client)
                else:
                    for chunk in response.chunks:
                        embed = discord.Embed(
                            description=chunk.content,
                            color=discord.Color.blue()
                        )
                        if self.voice_config.auto_detect:
                            embed.set_footer(text=f"Idioma detectado: {language}")
                        await ctx.send(embed=embed)
                    
            except Exception as e:
                logger.error(f"Error in ask_ai: {e}")
                await ctx.send(f"Erro ao processar sua pergunta: {str(e)}")

    @commands.hybrid_command(name='chat')
    @commands.has_permissions(administrator=True)
    async def toggle_chat_mode(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Ativa/desativa modo chat com IA no canal"""
        target_channel = channel or ctx.channel
        
        if target_channel.id in self.ai_chat_channels:
            self.ai_chat_channels.remove(target_channel.id)
            await ctx.send(f"Chat com IA desativado em {target_channel.mention}")
        else:
            self.ai_chat_channels.add(target_channel.id)
            await ctx.send(f"Chat com IA ativado em {target_channel.mention}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Processa mensagens em canais com modo chat ativo"""
        if message.author.bot or message.channel.id not in self.ai_chat_channels:
            return

        async with message.channel.typing():
            try:
                response, language = await self.process_ai_response(message.channel, message.content)
                if not response:
                    return
                
                voice_client = self.voice_connections.get(message.guild.id)
                if voice_client and voice_client.is_connected():
                    await self.process_voice_response(message.channel, response.chunks, voice_client)
                else:
                    for chunk in response.chunks:
                        embed = discord.Embed(
                            description=chunk.content,
                            color=discord.Color.blue()
                        )
                        if self.voice_config.auto_detect:
                            embed.set_footer(text=f"Idioma detectado: {language}")
                        await message.reply(embed=embed)
                    
            except Exception as e:
                logger.error(f"Error in chat mode: {e}")
                await message.channel.send(f"Erro ao processar mensagem: {str(e)}")

async def setup(bot):
    await bot.add_cog(AI(bot))