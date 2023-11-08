from __future__ import annotations
from typing import TYPE_CHECKING

from core.group import CustomGroup
from core.decorators import is_not_blacklisted, is_logged_in, non_premium_cooldown
from components.paginator import Paginator
from resources.emojis import emojis

from discord import app_commands

if TYPE_CHECKING:
    from core.bot import FortniteBot
    from resources.extras import FortniteInteraction


# noinspection PyUnresolvedReferences
class MissionCommands(CustomGroup):

    KNOWN_THEATERS: tuple[str, ...] = ('Stonewood', 'Plankerton', 'Canny Valley', 'Twine Peaks')
    ALL_THEATERS: tuple[str, ...] = KNOWN_THEATERS + ('Ventures', )

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.choices(theater=[app_commands.Choice(name=theater, value=theater) for theater in ALL_THEATERS])
    @app_commands.describe(theater='Choose a specific zone (e.g. Twine Peaks) to view.')
    @app_commands.command(description='View today\'s Mission Alerts.')
    async def alert(self, interaction: FortniteInteraction, theater: app_commands.Choice[str] | None = None) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        mission_alerts = await interaction.client.mission_alerts()

        _kt = self.KNOWN_THEATERS
        if theater is None:
            pass
        elif theater.name == 'Ventures':
            mission_alerts = [mission for mission in mission_alerts if mission.theater not in _kt]
        else:
            mission_alerts = [mission for mission in mission_alerts if mission.theater == theater.name]

        embeds = []
        theaters: list[str] = sorted({m.theater for m in mission_alerts}, key=lambda t: _kt.index(t) if t in _kt else 4)
        for _theater in theaters:

            theater_missions = [mission for mission in mission_alerts if mission.theater == _theater]
            theater_missions.sort(key=lambda mission: mission.power)

            fields = self.mission_alerts_to_fields(theater_missions)
            embeds += interaction.client.fields_to_embeds(
                fields,
                field_limit=4,
                colour=interaction.client.colour(interaction.guild),
                description=f'**Theater:** `{_theater}`',
                author_name='Mission Alerts',
                author_icon=interaction.client.user.avatar.url)

        for embed in embeds:
            embed.set_footer(text=f'Page {embeds.index(embed) + 1} of {len(embeds)}')

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View today\'s VBuck alerts.')
    async def vbucks(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        mission_alerts = await interaction.client.mission_alerts()

        vbuck_missions = []
        vbuck_count = 0

        for mission in mission_alerts:
            for reward in mission.alert_rewards:
                if reward.name == 'VBucks':
                    vbuck_missions.append(mission)
                    vbuck_count += reward.quantity
                    break

        fields = self.mission_alerts_to_fields(vbuck_missions, show_theater=True)
        embeds = interaction.client.fields_to_embeds(
            fields,
            field_limit=4,
            colour=interaction.client.colour(interaction.guild),
            description=f'**Total VBucks:** `{vbuck_count}`',
            author_name='VBuck Alerts',
            author_icon=emojis['vbuck_url'])

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View today\'s legendary/mythic survivor alerts.')
    async def survivors(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        mission_alerts = await interaction.client.mission_alerts()

        legendary_survivor_missions = []

        for mission in mission_alerts:
            for reward in mission.alert_rewards:
                if reward.rarity in ('mythic', 'legendary') and reward.type == 'Survivor':
                    legendary_survivor_missions.append(mission)
                    break

        fields = self.mission_alerts_to_fields(legendary_survivor_missions, show_theater=True)
        embeds = interaction.client.fields_to_embeds(
            fields,
            field_limit=4,
            colour=interaction.client.colour(interaction.guild),
            description=f'**Total Missions:** `{len(legendary_survivor_missions)}`',
            author_name='Survivor Alerts',
            author_icon=emojis['survivor_url'])

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View today\'s legendary schematic alerts.')
    async def schematics(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        mission_alerts = await interaction.client.mission_alerts()

        legendary_schematic_missions = []

        for mission in mission_alerts:
            for reward in mission.alert_rewards:
                if reward.rarity == 'legendary' and 'Schematic' in reward.template_id:
                    legendary_schematic_missions.append(mission)
                    break

        fields = self.mission_alerts_to_fields(legendary_schematic_missions, show_theater=True)
        embeds = interaction.client.fields_to_embeds(
            fields,
            field_limit=4,
            colour=interaction.client.colour(interaction.guild),
            description=f'**Total Missions:** `{len(legendary_schematic_missions)}`',
            author_name='Schematic Alerts',
            author_icon=emojis['schematic_url'])

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))

    @non_premium_cooldown()
    @is_logged_in()
    @is_not_blacklisted()
    @app_commands.command(description='View today\'s legendary hero alerts.')
    async def heroes(self, interaction: FortniteInteraction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)

        mission_alerts = await interaction.client.mission_alerts()

        legendary_hero_missions = []

        for mission in mission_alerts:
            for reward in mission.alert_rewards:
                if reward.rarity == 'legendary' and 'Hero' in reward.template_id:
                    legendary_hero_missions.append(mission)
                    break

        fields = self.mission_alerts_to_fields(legendary_hero_missions, show_theater=True)
        embeds = interaction.client.fields_to_embeds(
            fields,
            field_limit=4,
            colour=interaction.client.colour(interaction.guild),
            description=f'**Total Missions:** `{len(legendary_hero_missions)}`',
            author_name='Hero Alerts',
            author_icon=emojis['hero_url'])

        await interaction.followup.send(embed=embeds[0], view=Paginator(interaction, embeds))


async def setup(bot: FortniteBot) -> None:
    bot.tree.add_command(MissionCommands(name='missions'))
