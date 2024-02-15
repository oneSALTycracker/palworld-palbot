import asyncio
import json
import os
import logging
import nextcord
from nextcord.ext import commands
from util.gamercon_async import GameRCON
from nextcord import Game

class ConnectCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.servers = self.load_config()
        self.last_seen_players = {}

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.monitor_player_joins())

    async def test_rcon_connection(self, server_name):
        server_info = self.servers.get(server_name)
        if server_info:
            try:
                response = await self.run_command(server_info)
                logging.info(f"Test RCON Response: {response}")
            except Exception as e:
                logging.error(f"Error during RCON test: {e}")

    def load_config(self):
        config_path = os.path.join('data', 'config.json')
        with open(config_path) as config_file:
            config = json.load(config_file)
        return config["PALWORLD_SERVERS"]

    async def run_command(self, server):
        try:
            async with GameRCON(server["RCON_HOST"], server["RCON_PORT"], server["RCON_PASS"], timeout=10) as pc:
                response = await asyncio.wait_for(pc.send("ShowPlayers"), timeout=10.0)
                return response
        except Exception as e:
            logging.error(f"Error executing ShowPlayers command: {e}")
            return None

    async def monitor_player_joins(self):
        while True:
            total_players = 0
            for server_name, server_info in self.servers.items():
                current_players = await self.run_command(server_info)
                if current_players:
                    player_lines = current_players.strip().split('\n')
                    total_players += len(player_lines) - 1
            game_status = Game(f"Players Online: {total_players}")
            await self.bot.change_presence(status=nextcord.Status.online, activity=game_status)
            await asyncio.sleep(18)

    async def announce_new_players(self, server_name, current_players):
        new_players = self.extract_players(current_players)
        last_seen = self.last_seen_players.get(server_name, set())

        for player in new_players - last_seen:
            await self.announce_player_join(server_name, player)

        self.last_seen_players[server_name] = new_players

    def extract_players(self, player_data):
        players = set()
        lines = player_data.split('\n')[1:]
        for line in lines:
            if line.strip():
                parts = line.split(',')
                if len(parts) == 3:
                    name, _, steamid = parts
                    players.add((name.strip(), steamid.strip()))
        return players

    async def announce_player_join(self, server_name, player):
        name, steamid = player
        if "CONNECTION_CHANNEL" in self.servers[server_name]:
            announcement_channel_id = self.servers[server_name]["CONNECTION_CHANNEL"]
            channel = self.bot.get_channel(announcement_channel_id)
            if channel:
                await channel.send(f"Player joined on {server_name}: {name} (SteamID: {steamid})")

def setup(bot):
    bot.add_cog(ConnectCog(bot))
