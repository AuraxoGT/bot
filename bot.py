import discord
from discord import app_commands
import asyncio

# --- CONFIGURATION ---
# Paste your Bot Token here. Treat this like a password!
BOT_TOKEN = proccess.env.TOKEN

# Paste the Server ID of the server you want to COPY FROM.
SOURCE_GUILD_ID = 1325850250027597845 # Replace with your Source Server ID

# Paste the Server ID of the server you want to COPY TO.
# !! THIS SERVER WILL BE MODIFIED. USE A NEW, EMPTY SERVER !!
TARGET_GUILD_ID = 1316845375511986287 # Replace with your Target Server ID
# --- END CONFIGURATION ---


# --- BOT SETUP ---
# Set up intents to fetch all necessary data
intents = discord.Intents.default()
intents.guilds = True # This intent includes access to roles and channels
intents.members = True # Required for permissions mapping

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
        # This is recommended for instant slash command updates.
        guild = discord.Object(id=SOURCE_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

client = MyClient(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('Bot is ready to receive commands.')
    print('------')

# --- THE CLONE COMMAND ---
@client.tree.command()
@app_commands.describe(
    confirmation="Type 'CONFIRM' to start the cloning process. This is for safety."
)
async def clone(interaction: discord.Interaction, confirmation: str):
    """Clones the roles and channels from the source server to the target server."""

    if interaction.guild_id != SOURCE_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the source server.", ephemeral=True)
        return

    if confirmation.upper() != "CONFIRM":
        await interaction.response.send_message("Cloning process aborted. Confirmation not provided.", ephemeral=True)
        return

    await interaction.response.send_message("Clone process initiated. This will take a while. Check your bot's console for progress.", ephemeral=True)

    source_guild = client.get_guild(SOURCE_GUILD_ID)
    target_guild = client.get_guild(TARGET_GUILD_ID)

    if not source_guild or not target_guild:
        print("Error: Bot is not in both guilds or the IDs are incorrect.")
        await interaction.followup.send("Error: Bot could not find both the source and target servers. Check your configuration and make sure the bot is in both servers.", ephemeral=True)
        return
        
    print(f"Starting clone from '{source_guild.name}' to '{target_guild.name}'")
    
    # --- Step 1: Clone Roles ---
    print("\n--- Cloning Roles ---")
    role_map = {} # To map old role IDs to new role IDs
    
    # We fetch roles and reverse them to create them in the correct hierarchical order (from bottom to top)
    source_roles = sorted(source_guild.roles, key=lambda r: r.position)

    # First, handle the @everyone role separately
    everyone_role_source = source_guild.default_role
    everyone_role_target = target_guild.default_role
    role_map[everyone_role_source.id] = everyone_role_target
    print(f"Mapped @everyone role.")
    
    # Update the @everyone role's permissions on the target server
    try:
        await everyone_role_target.edit(permissions=everyone_role_source.permissions)
        print(f"Updated permissions for @everyone role.")
    except discord.Forbidden:
        print(f"Failed to update permissions for @everyone role. Check bot permissions.")

    # Now clone all other roles
    for role in source_roles:
        if role.is_default(): # Skip @everyone as we handled it
            continue
        # ** FIX APPLIED HERE **
        if role.managed: # Skip roles managed by integrations (like other bots)
            print(f"Skipping managed role: {role.name}")
            continue

        print(f"Creating role: {role.name}")
        try:
            new_role = await target_guild.create_role(
                name=role.name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable
            )
            role_map[role.id] = new_role
            await asyncio.sleep(1) # Basic rate-limiting
        except discord.Forbidden:
            print(f"Failed to create role {role.name}. Check bot permissions.")
        except Exception as e:
            print(f"An error occurred while creating role {role.name}: {e}")

    print("--- Role cloning complete. ---")


    # --- Step 2: Clone Categories and Channels ---
    print("\n--- Cloning Channels ---")
    
    # Clear existing channels in the target server (optional, but recommended for a clean clone)
    print("Deleting existing channels in target server...")
    for channel in target_guild.channels:
        try:
            await channel.delete()
            print(f"Deleted channel: #{channel.name}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Could not delete channel #{channel.name}: {e}")
    
    # We must clone categories first
    for category, channels_in_category in source_guild.by_category():
        new_category = None
        if category: # If channels are in a category
            print(f"Creating category: {category.name}")
            
            # Remap permission overwrites for the category
            overwrites = {}
            for role_or_member, perms in category.overwrites.items():
                if isinstance(role_or_member, discord.Role) and role_or_member.id in role_map:
                    overwrites[role_map[role_or_member.id]] = perms

            try:
                new_category = await target_guild.create_category(
                    name=category.name,
                    overwrites=overwrites
                )
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Failed to create category {category.name}: {e}")
                continue # Skip channels in this category if creation fails
        
        # Now clone channels within that category (or uncategorized channels)
        for channel in channels_in_category:
            print(f"Creating channel: #{channel.name} in category: {new_category.name if new_category else 'None'}")
            
            # Remap permission overwrites for the channel
            channel_overwrites = {}
            for role_or_member, perms in channel.overwrites.items():
                # We only map roles, not individual members, for simplicity.
                if isinstance(role_or_member, discord.Role) and role_or_member.id in role_map:
                    channel_overwrites[role_map[role_or_member.id]] = perms
            
            try:
                if isinstance(channel, discord.TextChannel):
                    await target_guild.create_text_channel(
                        name=channel.name,
                        topic=channel.topic,
                        slowmode_delay=channel.slowmode_delay,
                        nsfw=channel.nsfw,
                        category=new_category,
                        overwrites=channel_overwrites
                    )
                elif isinstance(channel, discord.VoiceChannel):
                    await target_guild.create_voice_channel(
                        name=channel.name,
                        user_limit=channel.user_limit,
                        bitrate=channel.bitrate,
                        category=new_category,
                        overwrites=channel_overwrites
                    )
                await asyncio.sleep(1) # Basic rate-limiting
            except Exception as e:
                print(f"Failed to create channel {channel.name}: {e}")

    print("--- Channel cloning complete. ---")
    print("\n✅✅✅ CLONING PROCESS FINISHED! ✅✅✅")


# --- RUN THE BOT ---
client.run(BOT_TOKEN)
