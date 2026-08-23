from __future__ import annotations

from typing import Any

import discord

VLR_RED = 0xFF4655
VLR_BLUE = 0x5865F2
VLR_GREEN = 0x57F287
VLR_GOLD = 0xFEE75C


def _logo_url(logo: str | None) -> str | None:
    if not logo:
        return None
    if logo.startswith("//"):
        return f"https:{logo}"
    return logo


def _vlr_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    normalized = path if path.startswith("/") else f"/{path}"
    return f"https://www.vlr.gg{normalized}"


def _format_series(name: str | None) -> str:
    if not name:
        return "—"
    return name.replace("-", " · ")


def _winner_name(team1: str, team2: str, score1: str | int, score2: str | int) -> str | None:
    try:
        s1, s2 = int(score1), int(score2)
    except (TypeError, ValueError):
        return None
    if s1 > s2:
        return team1
    if s2 > s1:
        return team2
    return None


def news_embed(article: dict[str, Any]) -> discord.Embed:
    description = article.get("description") or "No summary available."
    url = _vlr_url(article.get("url_path"))
    if url:
        description = f"{description}\n\n[Read on vlr.gg →]({url})"
    embed = discord.Embed(
        title=article.get("title", "Valorant News"),
        description=description,
        color=VLR_RED,
        url=url,
    )
    embed.set_author(name="vlr.gg News")
    date = article.get("date", "")
    author = article.get("author", "")
    footer = f"{date} · By {author}" if author else date
    embed.set_footer(text=footer or "Valorant Esports")
    return embed


def upcoming_embed(match: dict[str, Any]) -> discord.Embed:
    team1 = match.get("team1", "TBD")
    team2 = match.get("team2", "TBD")
    embed = discord.Embed(
        title=f"📅 {team1} vs {team2}",
        description=match.get("match_event", ""),
        color=VLR_BLUE,
        url=_vlr_url(match.get("match_page")),
    )
    embed.set_author(name="Upcoming Match")
    embed.add_field(name="Series", value=_format_series(match.get("match_series")), inline=False)
    embed.add_field(name="Starts In", value=match.get("time_until_match", "TBD"), inline=True)
    embed.add_field(name="Scheduled", value=match.get("unix_timestamp", "—"), inline=True)
    embed.set_footer(text="Match schedule via vlr.gg")
    return embed


def _map_results_summary(maps: list[dict[str, Any]], team1: str, team2: str) -> str:
    lines: list[str] = []
    for idx, game in enumerate(maps, start=1):
        t1, t2 = _map_round_score(game.get("score"))
        map_name = game.get("map_name", f"Map {idx}")
        lines.append(f"**{map_name}** — {t1} : {t2}")
    return "\n".join(lines) if lines else "—"


def _top_performers(maps: list[dict[str, Any]], limit: int = 3) -> str:
    performers: list[tuple[int, str]] = []
    for game in maps:
        for team_players in game.get("players", {}).values():
            for player in team_players:
                acs_raw = player.get("acs")
                if not acs_raw:
                    continue
                try:
                    acs = int(str(acs_raw).replace(",", ""))
                except ValueError:
                    continue
                name = player.get("name", "?")
                agent = player.get("agent") or "?"
                performers.append((acs, f"**{name}** ({agent}) · ACS {acs_raw}"))
    if not performers:
        return "—"
    performers.sort(key=lambda item: item[0], reverse=True)
    return "\n".join(line for _, line in performers[:limit])


def result_embed(match: dict[str, Any], details: dict[str, Any] | None = None) -> discord.Embed:
    team1 = match.get("team1", "Team 1")
    team2 = match.get("team2", "Team 2")
    score1 = match.get("score1", "?")
    score2 = match.get("score2", "?")
    winner = _winner_name(team1, team2, score1, score2)

    embed = discord.Embed(
        title=f"🏁 {team1} {score1} — {score2} {team2}",
        description=match.get("tournament_name", ""),
        color=VLR_GOLD if winner else discord.Color.dark_grey(),
        url=_vlr_url(match.get("match_page")),
    )
    embed.set_author(name="Match Result")
    icon = _logo_url(match.get("tournament_icon"))
    if icon:
        embed.set_thumbnail(url=icon)

    if winner:
        embed.add_field(name="Winner", value=f"**{winner}**", inline=False)

    embed.add_field(name="Series", value=_format_series(match.get("round_info")), inline=True)
    embed.add_field(name="Completed", value=match.get("time_completed", "—"), inline=True)

    if details and details.get("maps"):
        maps = details["maps"]
        embed.add_field(name="Maps", value=_map_results_summary(maps, team1, team2), inline=False)
        top = _top_performers(maps)
        if top != "—":
            embed.add_field(name="Top Performers", value=top, inline=False)

    embed.set_footer(text="Final result via vlr.gg")
    return embed


def _format_player_line(player: dict[str, Any]) -> str:
    name = player.get("name", "Unknown")
    agent = player.get("agent") or "?"
    kills = player.get("kills") or "-"
    deaths = player.get("deaths") or "-"
    assists = player.get("assists") or "-"
    acs = player.get("acs") or ""
    rating = player.get("rating") or ""

    kda = f"{kills}/{deaths}/{assists}"
    if acs:
        return f"**{name}** ({agent})\nACS **{acs}** · K/D/A {kda}"
    if rating:
        return f"**{name}** ({agent})\nR:{rating} · K/D/A {kda}"
    if kills != "-":
        return f"**{name}** ({agent})\nK/D/A {kda}"
    return f"**{name}** ({agent})\n—"


def _map_round_score(score: dict[str, Any] | None) -> tuple[int | str, int | str]:
    if not score:
        return "?", "?"
    t1 = score.get("team1", "?")
    t2 = score.get("team2", "?")
    if isinstance(t1, dict):
        t1 = t1.get("total", "?")
    if isinstance(t2, dict):
        t2 = t2.get("total", "?")
    return t1, t2


def _current_live_map(maps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for game in reversed(maps):
        t1, t2 = _map_round_score(game.get("score"))
        try:
            s1, s2 = int(t1 or 0), int(t2 or 0)
        except (TypeError, ValueError):
            continue
        if s1 < 13 and s2 < 13 and (s1 > 0 or s2 > 0):
            return game

        players = game.get("players", {})
        for team_players in players.values():
            if any(p.get("kills") for p in team_players):
                if s1 < 13 and s2 < 13:
                    return game
    return maps[-1] if maps else None


def _team_player_lines(players: list[dict[str, Any]]) -> str:
    lines = [_format_player_line(p) for p in players[:5]]
    return "\n\n".join(lines) if lines else "—"


def live_embed(live: dict[str, Any], details: dict[str, Any] | None = None) -> discord.Embed:
    team1 = live.get("team1", "Team 1")
    team2 = live.get("team2", "Team 2")
    score1 = live.get("score1", "0")
    score2 = live.get("score2", "0")
    current_map = live.get("current_map", "Unknown")
    map_number = live.get("map_number", "?")

    if details and details.get("teams"):
        for idx, team in enumerate(details["teams"][:2]):
            name = team.get("name")
            if idx == 0 and name:
                team1 = name
            elif idx == 1 and name:
                team2 = name

    embed = discord.Embed(
        title=f"🔴 LIVE — {team1} {score1} — {score2} {team2}",
        description=live.get("match_event", ""),
        color=VLR_GREEN,
        url=_vlr_url(live.get("match_page")),
    )
    embed.add_field(name="Series", value=_format_series(live.get("match_series")), inline=False)

    current_game = _current_live_map(details.get("maps", [])) if details else None
    if current_game:
        current_map = current_game.get("map_name", current_map)
        map_number = details.get("maps", []).index(current_game) + 1 if details else map_number
        t1_score, t2_score = _map_round_score(current_game.get("score"))
        embed.add_field(
            name=f"Map {map_number}: {current_map}",
            value=f"**{team1}** {t1_score} — {t2_score} **{team2}**",
            inline=False,
        )
    else:
        embed.add_field(name="Map", value=f"Map {map_number}: {current_map}", inline=True)
        embed.add_field(
            name="Round Score",
            value=(
                f"{team1}: CT {live.get('team1_round_ct', '?')} / T {live.get('team1_round_t', '?')}\n"
                f"{team2}: CT {live.get('team2_round_ct', '?')} / T {live.get('team2_round_t', '?')}"
            ),
            inline=True,
        )

    logo1 = _logo_url(live.get("team1_logo"))
    logo2 = _logo_url(live.get("team2_logo"))
    if details and details.get("teams"):
        if len(details["teams"]) > 0:
            logo1 = _logo_url(details["teams"][0].get("logo")) or logo1
        if len(details["teams"]) > 1:
            logo2 = _logo_url(details["teams"][1].get("logo")) or logo2
    if logo1:
        embed.set_thumbnail(url=logo1)
    if logo2:
        embed.set_author(name="Live Match", icon_url=logo2)

    if current_game:
        players = current_game.get("players", {})
        team1_players = players.get("team1", [])
        team2_players = players.get("team2", [])

        if team1_players or team2_players:
            embed.add_field(name=f"{team1}", value=_team_player_lines(team1_players), inline=True)
            embed.add_field(name=f"{team2}", value=_team_player_lines(team2_players), inline=True)

    embed.set_footer(text="Live score updates automatically")
    return embed


def status_embed(title: str, description: str, *, ok: bool = True) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=VLR_GREEN if ok else VLR_RED,
    )
