from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import embeds
from config import (
    DISCORD_TOKEN,
    LIVE_POLL_INTERVAL,
    NEWS_POLL_INTERVAL,
    RESULTS_POLL_INTERVAL,
    UPCOMING_POLL_INTERVAL,
    VLR_API_BASE,
)
from storage import all_configured_guilds, get_guild_config, update_guild_config
from vlr_client import VLRClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("valorant-bot")

MAX_TRACKED_ITEMS = 200


class ValorantBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)
        self.vlr = VLRClient(VLR_API_BASE)

    async def setup_hook(self) -> None:
        await self.vlr.start()
        await self.tree.sync()
        news_loop.start()
        live_loop.start()
        upcoming_loop.start()
        results_loop.start()
        log.info("Slash commands synced and background tasks started")

    async def close(self) -> None:
        for loop in (news_loop, live_loop, upcoming_loop, results_loop):
            loop.cancel()
        await self.vlr.close()
        await super().close()

    async def on_ready(self) -> None:
        log.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "?")
        log.info("Using VLR API at %s", VLR_API_BASE)


bot = ValorantBot()


def _trim_list(items: list[str], limit: int = MAX_TRACKED_ITEMS) -> list[str]:
    return items[-limit:]


async def _result_embed_for_match(match: dict) -> discord.Embed:
    match_page = match.get("match_page", "")
    match_id = match.get("match_id") or bot.vlr.extract_match_id(match_page)
    details = None
    if match_id:
        try:
            details = await bot.vlr.match_details(match_id)
        except Exception as exc:
            log.debug("Result details unavailable for %s: %s", match_id, exc)
    return embeds.result_embed(match, details)


async def _get_channel(bot: ValorantBot, guild_id: int, channel_id: int | None) -> discord.TextChannel | None:
    if not channel_id:
        return None
    channel = bot.get_channel(channel_id)
    if channel is None:
        guild = bot.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
    return channel if isinstance(channel, discord.TextChannel) else None


def _channel_permissions_ok(guild: discord.Guild, *channels: discord.TextChannel) -> bool:
    for channel in channels:
        perms = channel.permissions_for(guild.me)
        if not perms.send_messages or not perms.embed_links:
            return False
    return True


def _format_channel(channel: discord.TextChannel | None) -> str:
    return channel.mention if channel else "Not set — run `/setup`"


@bot.tree.command(name="setup", description="Configure bot channels for this server")
@app_commands.describe(
    news_channel="Channel for Valorant news articles",
    live_channel="Channel for live match scores and player stats",
    upcoming_channel="Channel for upcoming / scheduled matches",
    results_channel="Channel for completed match results",
)
async def setup(
    interaction: discord.Interaction,
    news_channel: discord.TextChannel,
    live_channel: discord.TextChannel,
    upcoming_channel: discord.TextChannel,
    results_channel: discord.TextChannel,
) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    channels = (news_channel, live_channel, upcoming_channel, results_channel)
    if not _channel_permissions_ok(interaction.guild, *channels):
        await interaction.response.send_message(
            "I need **Send Messages** and **Embed Links** permission in all four channels.",
            ephemeral=True,
        )
        return

    update_guild_config(
        interaction.guild.id,
        news_channel_id=news_channel.id,
        live_channel_id=live_channel.id,
        upcoming_channel_id=upcoming_channel.id,
        results_channel_id=results_channel.id,
    )
    await interaction.response.send_message(
        embed=embeds.status_embed(
            "Setup complete",
            f"**News:** {news_channel.mention}\n"
            f"**Live:** {live_channel.mention}\n"
            f"**Upcoming:** {upcoming_channel.mention}\n"
            f"**Results:** {results_channel.mention}\n\n"
            "The bot will now post automatically. Use `/status` to verify the API connection.",
        ),
    )


@bot.tree.command(name="status", description="Check bot and API status")
async def status(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)
    guild_id = interaction.guild.id
    news_channel = await _get_channel(bot, guild_id, config.get("news_channel_id"))
    live_channel = await _get_channel(bot, guild_id, config.get("live_channel_id"))
    upcoming_channel = await _get_channel(bot, guild_id, config.get("upcoming_channel_id"))
    results_channel = await _get_channel(bot, guild_id, config.get("results_channel_id"))

    try:
        health = await bot.vlr.health()
        api_ok = True
        api_text = "\n".join(f"• {name}: **{info.get('status', '?')}**" for name, info in health.items())
    except Exception as exc:
        api_ok = False
        api_text = f"Could not reach API at `{VLR_API_BASE}`\n`{exc}`"

    desc = (
        f"**News:** {_format_channel(news_channel)}\n"
        f"**Live:** {_format_channel(live_channel)}\n"
        f"**Upcoming:** {_format_channel(upcoming_channel)}\n"
        f"**Results:** {_format_channel(results_channel)}\n\n"
        f"**VLR API:**\n{api_text}"
    )
    await interaction.response.send_message(embed=embeds.status_embed("Bot Status", desc, ok=api_ok), ephemeral=True)


@bot.tree.command(name="test-news", description="Post the latest news article now (admin test)")
@app_commands.default_permissions(manage_guild=True)
async def test_news(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Server only.", ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)
    channel = await _get_channel(bot, interaction.guild.id, config.get("news_channel_id"))
    if not channel:
        await interaction.response.send_message("Run `/setup` first.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        articles = await bot.vlr.news()
        if not articles:
            await interaction.followup.send("No news found.", ephemeral=True)
            return
        await channel.send(embed=embeds.news_embed(articles[0]))
        await interaction.followup.send("Posted latest article.", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"Failed: {exc}", ephemeral=True)


@bot.tree.command(name="test-matches", description="Post sample live/upcoming/result matches now (admin test)")
@app_commands.default_permissions(manage_guild=True)
async def test_matches(interaction: discord.Interaction) -> None:
    if not interaction.guild:
        await interaction.response.send_message("Server only.", ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)
    guild_id = interaction.guild.id
    live_channel = await _get_channel(bot, guild_id, config.get("live_channel_id"))
    upcoming_channel = await _get_channel(bot, guild_id, config.get("upcoming_channel_id"))
    results_channel = await _get_channel(bot, guild_id, config.get("results_channel_id"))
    if not live_channel or not upcoming_channel or not results_channel:
        await interaction.response.send_message("Run `/setup` with all four channels first.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        live = await bot.vlr.matches("live_score")
        upcoming = await bot.vlr.matches("upcoming")
        results = await bot.vlr.matches("results")
        count = 0

        for match in live[:2]:
            match_id = bot.vlr.extract_match_id(match.get("match_page", ""))
            details = await bot.vlr.match_details(match_id) if match_id else None
            await live_channel.send(embed=embeds.live_embed(match, details))
            count += 1

        for match in upcoming[:2]:
            await upcoming_channel.send(embed=embeds.upcoming_embed(match))
            count += 1

        for match in results[:2]:
            await results_channel.send(embed=await _result_embed_for_match(match))
            count += 1

        await interaction.followup.send(f"Posted {count} match embed(s) to live/upcoming/results channels.", ephemeral=True)
    except Exception as exc:
        await interaction.followup.send(f"Failed: {exc}", ephemeral=True)


@tasks.loop(seconds=NEWS_POLL_INTERVAL)
async def news_loop() -> None:
    await _poll_news()


@tasks.loop(seconds=LIVE_POLL_INTERVAL)
async def live_loop() -> None:
    await _poll_live()


@tasks.loop(seconds=UPCOMING_POLL_INTERVAL)
async def upcoming_loop() -> None:
    await _poll_upcoming()


@tasks.loop(seconds=RESULTS_POLL_INTERVAL)
async def results_loop() -> None:
    await _poll_results()


@news_loop.before_loop
@live_loop.before_loop
@upcoming_loop.before_loop
@results_loop.before_loop
async def before_loops() -> None:
    await bot.wait_until_ready()


async def _poll_news() -> None:
    try:
        articles = await bot.vlr.news()
    except Exception as exc:
        log.warning("News poll failed: %s", exc)
        return

    for guild_id_str, config in all_configured_guilds().items():
        channel_id = config.get("news_channel_id")
        if not channel_id:
            continue

        guild_id = int(guild_id_str)
        channel = await _get_channel(bot, guild_id, channel_id)
        if not channel:
            continue

        posted = set(config.get("posted_news", []))
        new_urls: list[str] = []

        for article in reversed(articles):
            url = article.get("url_path")
            if not url or url in posted:
                continue
            try:
                await channel.send(embed=embeds.news_embed(article))
                new_urls.append(url)
                await asyncio.sleep(1)
            except discord.HTTPException as exc:
                log.warning("Failed to post news in guild %s: %s", guild_id, exc)

        if new_urls:
            posted.update(new_urls)
            update_guild_config(guild_id, posted_news=_trim_list(list(posted)))


async def _poll_live() -> None:
    try:
        live_matches = await bot.vlr.matches("live_score")
    except Exception as exc:
        log.warning("Live poll failed: %s", exc)
        return

    for guild_id_str, config in all_configured_guilds().items():
        channel_id = config.get("live_channel_id")
        if not channel_id:
            continue

        guild_id = int(guild_id_str)
        channel = await _get_channel(bot, guild_id, channel_id)
        if not channel:
            continue

        live_messages: dict[str, str] = dict(config.get("live_messages", {}))
        active_ids = set()

        for match in live_matches:
            match_page = match.get("match_page", "")
            match_id = match.get("match_id") or bot.vlr.extract_match_id(match_page)
            if not match_id:
                continue

            active_ids.add(match_id)
            details = None
            try:
                details = await bot.vlr.match_details(match_id)
            except Exception as exc:
                log.debug("Match details unavailable for %s: %s", match_id, exc)

            embed = embeds.live_embed(match, details)
            msg_id = live_messages.get(match_id)

            try:
                if msg_id:
                    try:
                        msg = await channel.fetch_message(int(msg_id))
                        await msg.edit(embed=embed)
                        continue
                    except discord.NotFound:
                        pass

                msg = await channel.send(embed=embed)
                live_messages[match_id] = str(msg.id)
            except discord.HTTPException as exc:
                log.warning("Failed live update in guild %s: %s", guild_id, exc)

        # Clean up finished live messages from tracking
        stale = [mid for mid in live_messages if mid not in active_ids]
        for mid in stale:
            live_messages.pop(mid, None)

        update_guild_config(guild_id, live_messages=live_messages)


async def _poll_upcoming() -> None:
    try:
        upcoming = await bot.vlr.matches("upcoming")
    except Exception as exc:
        log.warning("Upcoming poll failed: %s", exc)
        return

    for guild_id_str, config in all_configured_guilds().items():
        channel_id = config.get("upcoming_channel_id")
        if not channel_id:
            continue

        guild_id = int(guild_id_str)
        channel = await _get_channel(bot, guild_id, channel_id)
        if not channel:
            continue

        posted = set(config.get("posted_upcoming", []))
        new_keys: list[str] = []

        for match in upcoming:
            key = match.get("match_page") or f"{match.get('team1')}-{match.get('team2')}-{match.get('unix_timestamp')}"
            if key in posted:
                continue
            try:
                await channel.send(embed=embeds.upcoming_embed(match))
                new_keys.append(key)
                await asyncio.sleep(1)
            except discord.HTTPException as exc:
                log.warning("Failed upcoming post in guild %s: %s", guild_id, exc)

        if new_keys:
            posted.update(new_keys)
            update_guild_config(guild_id, posted_upcoming=_trim_list(list(posted)))


async def _poll_results() -> None:
    try:
        results = await bot.vlr.matches("results")
    except Exception as exc:
        log.warning("Results poll failed: %s", exc)
        return

    for guild_id_str, config in all_configured_guilds().items():
        channel_id = config.get("results_channel_id")
        if not channel_id:
            continue

        guild_id = int(guild_id_str)
        channel = await _get_channel(bot, guild_id, channel_id)
        if not channel:
            continue

        posted = set(config.get("posted_results", []))
        new_keys: list[str] = []

        for match in results:
            key = match.get("match_page") or f"{match.get('team1')}-{match.get('team2')}-{match.get('time_completed')}"
            if key in posted:
                continue
            try:
                embed = await _result_embed_for_match(match)
                await channel.send(embed=embed)
                new_keys.append(key)
                await asyncio.sleep(1)
            except discord.HTTPException as exc:
                log.warning("Failed result post in guild %s: %s", guild_id, exc)

        if new_keys:
            posted.update(new_keys)
            update_guild_config(guild_id, posted_results=_trim_list(list(posted)))


def main() -> None:
    if not DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token.")

    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
