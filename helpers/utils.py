import discord

async def create_text_channel_options(guild):
    options = []
    for category in guild.categories:
        options.append(discord.SelectOption(
            label=category.name,
            value=f"category_{category.id}",
            description="Selecionar todos os canais desta categoria"
        ))
        for channel in category.text_channels:
            options.append(discord.SelectOption(
                label=channel.name,
                value=str(channel.id),
                description=f"Canal em {category.name}"
            ))
    return options