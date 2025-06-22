import discord
from discord.ext import commands
import yt_dlp
import re
import os
import asyncio
import requests 

# Nustatykite savo boto tokeną čia
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Nustatykite laikinų failų katalogą
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Discord DM failo dydžio limitas baitais (bazinis 8 MB botui)
DISCORD_FILE_LIMIT = 8 * 1024 * 1024 # 8 MB

# Catbox.moe API URL
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"

# Sukurkite bot'o egzempliorių
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def upload_to_catbox(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = {'reqtype': 'fileupload'}
            files = {'fileToUpload': (os.path.basename(filepath), f)}
            
            response = requests.post(CATBOX_UPLOAD_URL, data=data, files=files)
            response.raise_for_status() 

            upload_url = response.text.strip()
            
            if upload_url.startswith("https://"):
                return upload_url
            else:
                print(f"Catbox įkėlimo klaida: {upload_url}")
                return None
    except requests.exceptions.RequestException as e:
        print(f"Catbox užklausos klaida: {e}")
        return None
    except Exception as e:
        print(f"Bendroji Catbox įkėlimo klaida: {e}")
        return None

@bot.event
async def on_ready():
    print(f'{bot.user} sėkmingai prisijungė prie Discord!')
    print(f'Boto ID: {bot.user.id}')
    print('Sveikas! Aš esu YouTube atsisiuntimo bot\'as.')
    print('Atsiųskite man YouTube vaizdo įrašo nuorodą ir aš pasiūlysiu parsisiųsti MP3 arba MP4.')
    print(f'Failai virš {DISCORD_FILE_LIMIT / (1024 * 1024):.0f} MB bus įkeliami į Catbox.moe.')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Apdoroti tik tiesiogines žinutes (DM)
    if isinstance(message.channel, discord.DMChannel):
        user_input = message.content.strip()

        youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|v\/|)([\w-]{11})(?:\S+)?"
        match = re.match(youtube_regex, user_input) 

        # Pirmiausia patikriname, ar tai YouTube nuoroda
        if match:
            url = user_input # Nuoroda yra user_input
            await message.channel.send(
                f"Gavau YouTube nuorodą: `{url}`.\n"
                "Ką norėtumėte atsisiųsti?\n"
                "**1️⃣ MP3 (garsas)**\n"
                "**2️⃣ MP4 (video)**"
            )

            def check(m):
                return m.author == message.author and m.channel == message.channel and m.content in ['1', '2']

            try:
                choice_message = await bot.wait_for('message', check=check, timeout=60.0)
                choice = choice_message.content

                await message.channel.send("Pradedamas atsisiuntimas... Tai gali užtrukti.")

                if choice == '1': # MP3
                    filename_template = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': filename_template,
                        'noplaylist': True,
                        'concurrent_fragment_downloads': 5,
                        'progress_hooks': [lambda d: print(f"MP3 atsisiuntimas: {d['status']}")]
                    }
                else: # MP4
                    filename_template = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'outtmpl': filename_template,
                        'noplaylist': True,
                        'concurrent_fragment_downloads': 5,
                        'progress_hooks': [lambda d: print(f"MP4 atsisiuntimas: {d['status']}")]
                    }
                
                filepath = None 
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(url, download=True)
                        filepath = ydl.prepare_filename(info_dict)
                        if not os.path.exists(filepath):
                            base_filename = os.path.splitext(filepath)[0]
                            possible_filepath_mp3 = base_filename + ".mp3"
                            possible_filepath_mp4 = base_filename + ".mp4"
                            if os.path.exists(possible_filepath_mp3):
                                filepath = possible_filepath_mp3
                            elif os.path.exists(possible_filepath_mp4):
                                filepath = possible_filepath_mp4
                            else:
                                await message.channel.send("Atsisiųstas failas nerastas. Įvyko klaida.")
                                return

                    filesize = os.path.getsize(filepath)
                    
                    if filesize > DISCORD_FILE_LIMIT: 
                        await message.channel.send(
                            f"Failas (`{os.path.basename(filepath)}`, "
                            f"{filesize / (1024 * 1024):.2f} MB) yra per didelis "
                            f"tiesioginiam siuntimui per Discord DM (maks. {DISCORD_FILE_LIMIT / (1024 * 1024):.0f} MB).\n" 
                            "Bandau įkelti failą į debesies saugyklą Catbox.moe..."
                        )
                        upload_url = await upload_to_catbox(filepath) 
                        if upload_url:
                            await message.channel.send(f"Failas sėkmingai įkeltas! Atsisiuntimo nuoroda: {upload_url}")
                        else:
                            await message.channel.send(
                                "Nepavyko įkelti failo į debesies saugyklą (Catbox.moe). "
                                "Atsiprašau, bet negaliu jums jo atsiųsti. "
                                "Failas yra serveryje, kuriame veikia bot'as."
                            )
                    else:
                        await message.channel.send("Atsisiuntimas baigtas! Siunčiu failą...",
                                                   file=discord.File(filepath))
                    
                    await asyncio.sleep(5) 
                    if filepath and os.path.exists(filepath): 
                        os.remove(filepath)
                        print(f"Ištrintas failas: {filepath}")

                except Exception as e:
                    await message.channel.send(f"Atsiprašau, įvyko klaida atsisiunčiant ar siunčiant failą: {e}")
                    print(f"Atsisiuntimo/siuntimo klaida: {e}")
                    if filepath and os.path.exists(filepath): 
                        os.remove(filepath)
                        print(f"Ištrintas failas po klaidos: {filepath}")

            except asyncio.TimeoutError:
                await message.channel.send("Nepasirinkote per nustatytą laiką. Prašome pabandyti dar kartą.")
        # Šis "else" blokas bus pasiektas TIK tada, jei pirminė žinutė NEBUVO YouTube nuoroda
        # ir NEBUVO '1' ar '2' (nes '1' ar '2' apdorojamas "wait_for" viduje).
        # Taip išvengiame atsakymo į boto paties siųstas žinutes.
        else:
            # Patikriname, ar vartotojo įvestis nėra "1" ar "2", kad bot'as nereaguotų į savo paties klausimus
            if user_input not in ['1', '2']:
                await message.channel.send("Atrodo, tai nėra galiojanti YouTube nuoroda. Prašome atsiųsti galiojančią nuorodą.")
    else:
        await message.channel.send("Prašome siųsti YouTube nuorodas man tiesioginėmis žinutėmis (DM).")

bot.run(DISCORD_TOKEN)
