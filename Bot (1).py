import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import datetime

# --- CONFIGURATION ---
TOKEN = 'Your_BOT_TOKEN_HERE'
OWNER_ID = 1406103686652104815
OWNERSHIP_ROLE_ID = 1471614589744451839
MOD_ROLE_ID = 1471482783984779276
class TXRPBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="$", intents=intents)
        
        # Initial Bot State
        self.stream_url = ""
        self.current_activity = "Watching over the Cloud! | /help for commands"
        self.current_status = discord.Status.online

    async def setup_hook(self):
        # Database Setup
        self.db = sqlite3.connect('levels.db')
        self.cursor = self.db.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                guild_id TEXT, 
                user_id TEXT, 
                xp INTEGER, 
                level INTEGER, 
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        self.db.commit()
        
        # Sync Slash Commands
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def on_ready(self):
        print(f"🚀 {self.user} is fully online and ready.")
        await self.update_presence()

    async def update_presence(self):
        activity = discord.Streaming(name=self.current_activity, url=self.stream_url)
        await self.change_presence(status=self.current_status, activity=activity)

bot = TXRPBot()

# --- XP LOGIC ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    bot.cursor.execute("SELECT xp FROM users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = bot.cursor.fetchone()

    if not row:
        bot.cursor.execute("INSERT INTO users VALUES (?, ?, 5, 1)", (guild_id, user_id))
    else:
        bot.cursor.execute("UPDATE users SET xp = xp + 5 WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    
    bot.db.commit()
    await bot.process_commands(message)

# --- SLASH COMMANDS ---

@bot.tree.command(name="help", description="List all available commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="TXRP Command List", color=discord.Color.from_str("#004bfa"))
    embed.add_field(name="👮 Staff", value="`/kick`, `/ban`, `/purge`, `/embed` cake", inline=False)
    embed.add_field(name="⚙️ Owner (DM Only)", value="`/setstatus`, `/seturl`, `/setpresence`, `/shutdown`", inline=False)
    embed.add_field(name="👤 User", value="`/rank`, `/link`, `/ping`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="embed", description="Create a custom staff embed message")
@app_commands.describe(title="Title of the embed", description="Main text content", color="Hex color (e.g. #7d2ae8)")
async def embed(interaction: discord.Interaction, title: str, description: str, color: str = "#004bfa"):
    if not any(role.id in [MOD_ROLE_ID, OWNERSHIP_ROLE_ID] for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Access Denied.", ephemeral=True)

    try:
        embed_color = discord.Color.from_str(color if color.startswith('#') else f"#{color}")
    except:
        embed_color = discord.Color.from_str("#004bfa")

    new_embed = discord.Embed(title=title, description=description, color=embed_color)
    new_embed.set_footer(text=f"Sent by {interaction.user.display_name}")
    
    await interaction.channel.send(embed=new_embed)
    await interaction.response.send_message("Embed sent!", ephemeral=True)

@bot.tree.command(name="rank", description="Check your current level and XP")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    bot.cursor.execute("SELECT xp, level FROM users WHERE guild_id = ? AND user_id = ?", 
                      (str(interaction.guild_id), str(target.id)))
    row = bot.cursor.fetchone()
    
    if row:
        await interaction.response.send_message(f"📊 **{target.display_name}** | Level: {row[1]} | XP: {row[0]}")
    else:
        await interaction.response.send_message("❌ No XP data found for this user.")

@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 {round(bot.latency * 1000)}ms")



# --- STAFF ACTIONS ---

@bot.tree.command(name="purge", description="Delete a number of messages")
async def purge(interaction: discord.Interaction, amount: int):
    if not any(role.id == OWNERSHIP_ROLE_ID for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Insufficient Permissions.", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🗑️ Purged {len(deleted)} messages.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not any(role.id == MOD_ROLE_ID for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 **{member.display_name}** has been kicked.")

@bot.tree.command(name="ban", description="Ban a member")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if not any(role.id == MOD_ROLE_ID for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 **{member.display_name}** has been banned.")

# --- OWNER COMMANDS (DM ONLY) ---

@bot.tree.command(name="setstatus", description="Change streaming text (Owner Only)")
async def setstatus(interaction: discord.Interaction, text: str):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Owner Only.", ephemeral=True)
    
    if interaction.guild:
        return await interaction.response.send_message("❌ This command must be used in DMs.", ephemeral=True)

    bot.current_activity = text
    await bot.update_presence()
    await interaction.response.send_message(f"✅ Status updated: **Streaming {text}**")

@bot.tree.command(name="setpresence", description="Change bot color (Owner Only)")
@app_commands.choices(mode=[
    app_commands.Choice(name="Online", value="online"),
    app_commands.Choice(name="Idle", value="idle"),
    app_commands.Choice(name="Do Not Disturb", value="dnd")
])
async def setpresence(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    if interaction.user.id != OWNER_ID: return
    
    status_map = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd
    }
    bot.current_status = status_map[mode.value]
    await bot.update_presence()
    await interaction.response.send_message(f"✅ Presence set to **{mode.name}**")

@bot.tree.command(name="shutdown", description="Turn off the bot (Owner Only)")
async def shutdown(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID: return
    await interaction.response.send_message("📴 Shutting down systems...")
    bot.db.close()
    await bot.close()

bot.run(TOKEN)