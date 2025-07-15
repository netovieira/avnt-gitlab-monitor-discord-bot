from discord import app_commands


def need_admin_permissions():
    async def predicate(interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    return app_commands.check(predicate)