import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import time
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# ========================================
# FLASK WEB SUNUCUSU
# ========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Sancak RP Botu Aktif!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# ========================================
# BOT AYARLARI
# ========================================

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========================================
# ESKİ BOT DEĞİŞKENLERİ
# ========================================

spam_aktif = False
silme_aktif = False
GUARD_AKTIF = False
KULLANICI_SON_ISLEM = {}
SPAM_KONTROL = {}

# ========================================
# YENİ SİSTEM AYARLARI (KENDİNE GÖRE DÜZENLE!)
# ========================================

TICKET_KATEGORI_ID = 0                          # Ticket kanallarının açılacağı kategori ID
LOG_KANAL_ID = 0                                # Log kanalı ID
YETKILI_ROLLER = ["Guard", "/Cmds"]             # IP Ban / Ban / Kick atabilecek roller
DESTEK_ROLLERI = ["Vise Team"]                  # Ticketları görebilecek roller (ÖRNEK)

# ========================================
# VERİTABANI
# ========================================

DB = "sancak_rp.db"

def db_kur():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (kanal_id INTEGER PRIMARY KEY, kullanici_id INTEGER, konu TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ipbanlar
                 (user_id INTEGER PRIMARY KEY, sebep TEXT, tarih TEXT)''')
    conn.commit()
    conn.close()

db_kur()

# ========================================
# YARDIMCI FONKSİYONLAR
# ========================================

def log_yaz(guild, mesaj):
    kanal = guild.get_channel(LOG_KANAL_ID)
    if kanal:
        asyncio.create_task(kanal.send(mesaj))

def rate_limit_kontrol(user_id):
    now = time.time()
    if user_id in KULLANICI_SON_ISLEM:
        if now - KULLANICI_SON_ISLEM[user_id] < 1:
            return False
    KULLANICI_SON_ISLEM[user_id] = now
    return True

async def spam_kontrol(message):
    if not GUARD_AKTIF:
        return False
    
    user_id = message.author.id
    now = time.time()
    
    if user_id in SPAM_KONTROL:
        if now - SPAM_KONTROL[user_id] < 5:
            return False
    SPAM_KONTROL[user_id] = now
    
    if user_id not in KULLANICI_SON_ISLEM:
        KULLANICI_SON_ISLEM[user_id] = []
    
    if not isinstance(KULLANICI_SON_ISLEM[user_id], list):
        KULLANICI_SON_ISLEM[user_id] = []
    
    KULLANICI_SON_ISLEM[user_id] = [t for t in KULLANICI_SON_ISLEM[user_id] if now - t < 5]
    KULLANICI_SON_ISLEM[user_id].append(now)
    
    if len(KULLANICI_SON_ISLEM[user_id]) > 5:
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=1), reason="Spam")
            await message.channel.send(f"{message.author.mention} spam yaptığın için 1 dakika susturuldun.")
            return True
        except:
            pass
    return False

async def kufur_kontrol(message):
    if not GUARD_AKTIF:
        return False
    YASAKLI_KELIMELER = ["aptal", "salak", "manyak", "gerizekalı", "mala", "amk", "sg", "siktir", "orospu", "pezevenk", "göt", "yarrak", "amcık"]
    for kelime in YASAKLI_KELIMELER:
        if kelime in message.content.lower():
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention} yasaklı kelime kullandın.")
                return True
            except:
                pass
    return False

async def link_kontrol(message):
    if not GUARD_AKTIF:
        return False
    YASAKLI_LINKLER = ["discord.gg/", "https://", "http://", ".com", ".net", ".org"]
    for link in YASAKLI_LINKLER:
        if link in message.content.lower():
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention} link paylaşmak yasak.")
                return True
            except:
                pass
    return False

def yikim_engeli():
    async def predicate(ctx):
        if GUARD_AKTIF:
            await ctx.send("Guard aktif. Yıkım komutları kapalı.")
            return False
        return True
    return commands.check(predicate)

# ========================================
# OLAYLAR
# ========================================

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!yardım | Sancak RP"))
    print(f'✅ Sancak RP Botu hazır: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if not rate_limit_kontrol(message.author.id):
        return
    
    if await spam_kontrol(message):
        return
    if await kufur_kontrol(message):
        return
    if await link_kontrol(message):
        return
    
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Yetkin yetmiyor, otur ağla.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Eksik argüman. Doğru kullanım: `{ctx.command.name} {ctx.command.signature}`")
    else:
        print(f"Hata: {error}")
        await ctx.send(f"Hata: {str(error)[:100]}")

# ========================================
# GUARD KOMUTU (ESKİ)
# ========================================

@bot.command()
@commands.has_permissions(administrator=True)
async def guard(ctx, durum: str = None):
    global GUARD_AKTIF
    if durum is None:
        await ctx.send(f"Guard {'aktif' if GUARD_AKTIF else 'pasif'}.")
        return
    if durum.lower() == "on":
        GUARD_AKTIF = True
        await ctx.send("Guard aktif. Yıkım komutları kapalı.")
    elif durum.lower() == "off":
        GUARD_AKTIF = False
        await ctx.send("Guard pasif. Yıkım komutları açık.")
    else:
        await ctx.send("!guard on veya !guard off yaz.")

# ========================================
# TICKET SİSTEMİ (YENİ)
# ========================================

class TicketButonlar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Oyun İçi Destek", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="ticket_oyun")
    async def oyun(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_olustur(interaction, "Oyun İçi Destek")

    @discord.ui.button(label="Teknik Destek", style=discord.ButtonStyle.secondary, emoji="🔧", custom_id="ticket_teknik")
    async def teknik(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_olustur(interaction, "Teknik Destek")

    @discord.ui.button(label="Donate Bilgi", style=discord.ButtonStyle.success, emoji="🛒", custom_id="ticket_donate")
    async def donate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_olustur(interaction, "Donate Bilgi")

    @discord.ui.button(label="AntiCheat", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="ticket_anticheat")
    async def anticheat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_olustur(interaction, "AntiCheat")


async def ticket_olustur(interaction: discord.Interaction, kategori: str):
    guild = interaction.guild
    user = interaction.user

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT kanal_id FROM tickets WHERE kullanici_id = ? AND durum = 'acik'", (user.id,))
    kayit = c.fetchone()
    if kayit:
        kanal = guild.get_channel(kayit[0])
        if kanal:
            await interaction.response.send_message(f"❌ Zaten açık bir ticketın var: {kanal.mention}", ephemeral=True)
            conn.close()
            return

    kategori_kanal = guild.get_channel(TICKET_KATEGORI_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    for rol_ismi in DESTEK_ROLLERI:
        rol = discord.utils.get(guild.roles, name=rol_ismi)
        if rol:
            overwrites[rol] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ticket_sayisi = len([k for k in guild.channels if k.name.startswith("ticket-")]) + 1
    kanal = await guild.create_text_channel(
        name=f"ticket-{ticket_sayisi:04d}",
        category=kategori_kanal,
        overwrites=overwrites
    )

    c.execute("INSERT INTO tickets (kanal_id, kullanici_id, konu, durum, tarih) VALUES (?, ?, ?, ?, ?)",
              (kanal.id, user.id, kategori, "acik", datetime.now().isoformat()))
    conn.commit()
    conn.close()

    embed = discord.Embed(
        title=f"🎫 Destek Talebi #{ticket_sayisi:04d}",
        description=f"{user.mention} tarafından **{kategori}** kategorisinde oluşturuldu.\n\n"
                    f"**Destek ID:** #{ticket_sayisi:04d}\n"
                    f"**Kategori:** {kategori}\n"
                    f"**Oluşturan:** {user.mention}\n"
                    f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sancak RP Destek Sistemi")

    view = TicketKontrol()
    await kanal.send(content=user.mention + " | Yetkililer en kısa sürede ilgilenecektir.", embed=embed, view=view)
    await interaction.response.send_message(f"✅ Ticketın açıldı: {kanal.mention}", ephemeral=True)
    log_yaz(guild, f"🎫 **Yeni Ticket:** {kanal.mention} - {user.mention} ({kategori})")


class TicketKontrol(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Claim", style=discord.ButtonStyle.secondary, emoji="🙋", custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ {interaction.user.mention} bu ticketı üstlendi.")

    @discord.ui.button(label="Beklemede", style=discord.ButtonStyle.primary, emoji="⏸️", custom_id="ticket_bekleme")
    async def bekleme(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"⏸️ Ticket **beklemede** olarak işaretlendi.")

    @discord.ui.button(label="İnceleniyor", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="ticket_inceleniyor")
    async def inceleniyor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"🔍 Ticket **inceleniyor**.")

    @discord.ui.button(label="Çözüldü", style=discord.ButtonStyle.success, emoji="✅", custom_id="ticket_cozuldu")
    async def cozuldu(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Ticket çözüldü olarak işaretlendi. Kanal 5 saniye içinde silinecek.")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_kapat")
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("🔒 Ticket kapatılıyor...")
        await asyncio.sleep(3)
        await interaction.channel.delete()


@bot.command()
@commands.has_permissions(administrator=True)
async def ticketkur(ctx):
    """Ticket panelini kurar."""
    embed = discord.Embed(
        title="🎫 Sancak RP Destek Sistemi",
        description="Bilet oluşturmadan önce aşağıdaki kuralları okuyunuz. Aşağıdaki butonlardan size uygun kategoriyi seçerek destek talebi oluşturabilirsiniz.\n\n"
                    "**Genel Kurallar:**\n"
                    "• Biletinizi **24 saat** içerisinde kontrol etmek zorundasınız.\n"
                    "• Yönetim üyelerine özel mesaj atmaktan kaçının.\n"
                    "• Sorunlarınızı bilet aracılığıyla iletişim kurun.\n\n"
                    "**Sorun Bildirimi:**\n"
                    "• Sorunu detaylı bir şekilde açıklayın.\n"
                    "• Gerekli bilgileri eksiksiz paylaşın.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sancak RP • Destek Sistemi")
    view = TicketButonlar()
    await ctx.send(embed=embed, view=view)

# ========================================
# IP BAN, BAN, KICK (Sadece Guard ve /Cmds)
# ========================================

def ipban_yetkisi_var_mi(member: discord.Member) -> bool:
    for rol in member.roles:
        if rol.name in YETKILI_ROLLER:
            return True
    return False


@bot.tree.command(name="ipban", description="Kullanıcıya IP ban atar (Sadece Guard ve /Cmds)")
@app_commands.describe(kullanici="Banlanacak kullanıcı", sebep="Ban sebebi")
async def ipban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not ipban_yetkisi_var_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu kullanmak için **Guard** veya **/Cmds** rolüne sahip olmalısın!", ephemeral=True)
        return

    guild = interaction.guild
    try:
        await guild.ban(kullanici, reason=f"[IP BAN] {sebep} | Yetkili: {interaction.user}")

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ipbanlar (user_id, sebep, tarih) VALUES (?, ?, ?)",
                  (kullanici.id, sebep, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title="🚫 IP BAN ATILDI",
            description=f"**Kullanıcı:** {kullanici.mention} (`{kullanici.id}`)\n"
                        f"**Sebep:** {sebep}\n"
                        f"**Yetkili:** {interaction.user.mention}\n"
                        f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Sancak RP • IP Ban Sistemi")
        await interaction.response.send_message(embed=embed)
        log_yaz(guild, f"🚫 **IP BAN:** {kullanici.mention} - {sebep} | Yetkili: {interaction.user.mention}")

    except discord.Forbidden:
        await interaction.response.send_message("❌ Bu kullanıcıyı banlayamıyorum (yetkim yetmiyor).", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="ban", description="Kullanıcıyı sunucudan banlar")
@app_commands.describe(kullanici="Banlanacak kullanıcı", sebep="Ban sebebi")
async def ban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not ipban_yetkisi_var_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu kullanmak için **Guard** veya **/Cmds** rolüne sahip olmalısın!", ephemeral=True)
        return

    guild = interaction.guild
    try:
        await guild.ban(kullanici, reason=f"{sebep} | Yetkili: {interaction.user}")
        embed = discord.Embed(
            title="🔨 BAN ATILDI",
            description=f"**Kullanıcı:** {kullanici.mention}\n**Sebep:** {sebep}\n**Yetkili:** {interaction.user.mention}",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed)
        log_yaz(guild, f"🔨 **BAN:** {kullanici.mention} - {sebep} | Yetkili: {interaction.user.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bu kullanıcıyı banlayamıyorum.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="kick", description="Kullanıcıyı sunucudan atar")
@app_commands.describe(kullanici="Atılacak kullanıcı", sebep="Atılma sebebi")
async def kick(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not ipban_yetkisi_var_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu kullanmak için **Guard** veya **/Cmds** rolüne sahip olmalısın!", ephemeral=True)
        return

    guild = interaction.guild
    try:
        await kullanici.kick(reason=f"{sebep} | Yetkili: {interaction.user}")
        embed = discord.Embed(
            title="👢 KICK ATILDI",
            description=f"**Kullanıcı:** {kullanici.mention}\n**Sebep:** {sebep}\n**Yetkili:** {interaction.user.mention}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        log_yaz(guild, f"👢 **KICK:** {kullanici.mention} - {sebep} | Yetkili: {interaction.user.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Bu kullanıcıyı atamıyorum.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

# ========================================
# ESKİ YIKIM KOMUTLARI
# ========================================

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sl(ctx):
    global silme_aktif
    if silme_aktif:
        await ctx.send("Silme işlemi zaten aktif.")
        return
    silme_aktif = True
    await ctx.send("Kanallar siliniyor... !sildur ile durdur.")
    for kanal in ctx.guild.channels:
        if not silme_aktif:
            break
        try:
            await kanal.delete()
            await asyncio.sleep(0.3)
        except:
            pass
    silme_aktif = False
    await ctx.send("Kanallar silindi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sildur(ctx):
    global silme_aktif
    silme_aktif = False
    await ctx.send("Silme durduruldu.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def spam(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("Spam zaten aktif.")
        return
    spam_aktif = True
    await ctx.send("Spam başladı. !dur ile durdur.")
    while spam_aktif:
        tasks = []
        for kanal in ctx.guild.text_channels:
            tasks.append(kanal.send("@everyone Valdo/Klowinc Siker .d"))
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.5)

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def dur(ctx):
    global spam_aktif
    spam_aktif = False
    await ctx.send("Spam durduruldu.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sıfırla(ctx):
    await ctx.send("Sunucu sıfırlanıyor...")
    for kanal in ctx.guild.channels:
        try:
            await kanal.delete()
        except:
            pass
    for rol in ctx.guild.roles:
        if rol.name != "@everyone":
            try:
                await rol.delete()
            except:
                pass
    for member in ctx.guild.members:
        if member != ctx.author and member != ctx.guild.me:
            try:
                await member.ban()
            except:
                pass
    await ctx.guild.edit(name="SIFIRLANDI")
    await ctx.send("Sunucu sıfırlandı.")

# ========================================
# EĞLENCE KOMUTLARI
# ========================================

@bot.command()
async def valdo(ctx):
    await ctx.send("YARRAMM VALDO BU KIM AMK")

@bot.command()
async def gonu(ctx):
    await ctx.send("2 GUNDE 48 CK ATAN ADAM")

@bot.command()
async def eternal(ctx):
    await ctx.send("FURKANIN NAMIDEGER BABASI")

@bot.command()
async def klowinc(ctx):
    await ctx.send("BU ADAMIN TASSAKLARINA BETON YETMEZ")

@bot.command()
async def doruk(ctx):
    await ctx.send("ARİEL BABAAAA")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def yardım(ctx):
    await ctx.send(
        "**🎯 Sancak RP Bot Komutları**\n\n"
        "**🛡️ Guard**\n"
        "!guard on/off\n\n"
        "**🎫 Ticket**\n"
        "!ticketkur - Ticket panelini kurar\n\n"
        "**🚫 Moderasyon**\n"
        "/ipban @kisi <sebep> - IP ban\n"
        "/ban @kisi <sebep> - Ban\n"
        "/kick @kisi <sebep> - Kick\n\n"
        "**⚠️ Yıkım**\n"
        "!sl, !sildur, !spam, !dur, !sıfırla\n\n"
        "**😂 Eğlence**\n"
        "!valdo, !gonu, !eternal, !klowinc, !doruk, !ping"
    )

# ========================================
# BAŞLATMA
# ========================================

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN ayarlanmamış!")
