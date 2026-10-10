import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# ========================================
# FLASK
# ========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Sancak RP Botu Aktif!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# ========================================
# AYARLAR
# ========================================

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========================================
# KENDİNE GÖRE DÜZENLE
# ========================================

TICKET_KATEGORI_ID = 0
LOG_KANAL_ID = 0
YETKILI_ROLLER = ["Guard", "/Cmds"]      # IP Ban, Ban, Kick, Rol Verme yetkisi
DESTEK_ROLLERI = ["Vise Team"]           # Ticket görebilecek roller (ÖRNEK)
ROL_VERME_YETKILILERI = ["Guard", "/Cmds"]  # Rol verebilecek roller (kim olduğu fark etmez)

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
    c.execute('''CREATE TABLE IF NOT EXISTS uyarilar
                 (user_id INTEGER, sebep TEXT, yetkili_id INTEGER, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS uyeler
                 (user_id INTEGER PRIMARY KEY, mesaj INTEGER DEFAULT 0, seviye INTEGER DEFAULT 1, xp INTEGER DEFAULT 0)''')
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

def yetkili_mi(member: discord.Member, roller: list) -> bool:
    for rol in member.roles:
        if rol.name in roller:
            return True
    return False

# ========================================
# BOT HAZIR
# ========================================

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/yardim | Sancak RP"))
    print(f'✅ Sancak RP Botu hazır: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")

# ========================================
# MESAJ TAKİBİ
# ========================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO uyeler (user_id, mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET mesaj = mesaj + 1", (message.author.id,))
    c.execute("SELECT mesaj, xp FROM uyeler WHERE user_id = ?", (message.author.id,))
    kayit = c.fetchone()
    if kayit:
        mesaj_sayisi, xp = kayit
        yeni_xp = xp + random.randint(5, 15)
        yeni_seviye = mesaj_sayisi // 50 + 1
        c.execute("UPDATE uyeler SET xp = ?, seviye = ? WHERE user_id = ?", (yeni_xp, yeni_seviye, message.author.id))
    conn.commit()
    conn.close()
    await bot.process_commands(message)

# ========================================
# SLASH: YARDIM
# ========================================

@bot.tree.command(name="yardim", description="Sancak RP Botu yardım menüsü")
async def yardim(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎯 Sancak RP Botu",
        description="Tüm komutlar:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎫 Ticket", value="`/ticketkur`", inline=False)
    embed.add_field(name="🚫 Moderasyon", value="`/ipban` `/ban` `/kick` `/uyari` `/uyarilar`", inline=False)
    embed.add_field(name="🎭 Rol Sistemi", value="`/rolver` `/rolal` `/toplurol`", inline=False)
    embed.add_field(name="📊 İstatistik", value="`/profil` `/seviye` `/liderlik`", inline=False)
    embed.add_field(name="🎉 Eğlence", value="`/zar` `/yazitura` `/espri`", inline=False)
    embed.add_field(name="⚙️ Yönetim", value="`/duyuru` `/anket` `/cekiliş`", inline=False)
    embed.set_footer(text="Sancak RP • Destek Sistemi")
    await interaction.response.send_message(embed=embed)

# ========================================
# TICKET SİSTEMİ
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
            await interaction.response.send_message(f"❌ Zaten açık ticketın var: {kanal.mention}", ephemeral=True)
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
        description=f"{user.mention} tarafından **{kategori}** kategorisinde oluşturuldu.",
        color=discord.Color.blue()
    )
    await kanal.send(content=user.mention, embed=embed, view=TicketKontrol())
    await interaction.response.send_message(f"✅ Ticket açıldı: {kanal.mention}", ephemeral=True)


class TicketKontrol(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Çözüldü", style=discord.ButtonStyle.success, emoji="✅", custom_id="ticket_cozuldu")
    async def cozuldu(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Ticket çözüldü.")
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


@bot.tree.command(name="ticketkur", description="Ticket panelini kurar")
@app_commands.default_permissions(administrator=True)
async def ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Sancak RP Destek Sistemi",
        description="Bilet oluşturmak için butonlara tıklayın.",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TicketButonlar())
    await interaction.response.send_message("✅ Panel kuruldu.", ephemeral=True)

# ========================================
# ROL VERME SİSTEMİ
# ========================================

@bot.tree.command(name="rolver", description="Kullanıcıya rol verir (Guard/Cmds)")
@app_commands.describe(kullanici="Rol verilecek kişi", rol="Verilecek rol")
async def rolver(interaction: discord.Interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, ROL_VERME_YETKILILERI):
        await interaction.response.send_message("❌ Bu komut için **Guard** veya **/Cmds** rolü gerekli!", ephemeral=True)
        return
    try:
        await kullanici.add_roles(rol)
        embed = discord.Embed(
            title="🎭 ROL VERİLDİ",
            description=f"**Kullanıcı:** {kullanici.mention}\n**Rol:** {rol.mention}\n**Yetkili:** {interaction.user.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        log_yaz(interaction.guild, f"🎭 **ROL VERİLDİ:** {kullanici.mention} - {rol.name} | {interaction.user.mention}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="rolal", description="Kullanıcıdan rol alır (Guard/Cmds)")
@app_commands.describe(kullanici="Rol alınacak kişi", rol="Alınacak rol")
async def rolal(interaction: discord.Interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, ROL_VERME_YETKILILERI):
        await interaction.response.send_message("❌ Bu komut için **Guard** veya **/Cmds** rolü gerekli!", ephemeral=True)
        return
    try:
        await kullanici.remove_roles(rol)
        embed = discord.Embed(
            title="🎭 ROL ALINDI",
            description=f"**Kullanıcı:** {kullanici.mention}\n**Rol:** {rol.mention}\n**Yetkili:** {interaction.user.mention}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        log_yaz(interaction.guild, f"🎭 **ROL ALINDI:** {kullanici.mention} - {rol.name} | {interaction.user.mention}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="toplurol", description="Tüm üyelere rol verir (Guard/Cmds)")
@app_commands.describe(rol="Verilecek rol")
async def toplurol(interaction: discord.Interaction, rol: discord.Role):
    if not yetkili_mi(interaction.user, ROL_VERME_YETKILILERI):
        await interaction.response.send_message("❌ Bu komut için **Guard** veya **/Cmds** rolü gerekli!", ephemeral=True)
        return
    await interaction.response.send_message(f"🎭 {rol.mention} rolü tüm üyelere veriliyor...", ephemeral=True)
    sayac = 0
    for uye in interaction.guild.members:
        if uye.bot:
            continue
        try:
            await uye.add_roles(rol)
            sayac += 1
            await asyncio.sleep(0.3)
        except:
            pass
    await interaction.channel.send(f"✅ {sayac} üyeye {rol.mention} rolü verildi.")
    log_yaz(interaction.guild, f"🎭 **TOPLU ROL:** {rol.name} - {sayac} üye | {interaction.user.mention}")

# ========================================
# MODERASYON
# ========================================

@bot.tree.command(name="ipban", description="IP ban atar (Guard/Cmds)")
async def ipban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Bu komut için **Guard** veya **/Cmds** rolü gerekli!", ephemeral=True)
        return
    try:
        await interaction.guild.ban(kullanici, reason=f"[IP BAN] {sebep} | {interaction.user}")
        embed = discord.Embed(title="🚫 IP BAN", description=f"{kullanici.mention} banlandı.\n**Sebep:** {sebep}", color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed)
        log_yaz(interaction.guild, f"🚫 IP BAN: {kullanici.mention} | {interaction.user.mention}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="ban", description="Ban atar (Guard/Cmds)")
async def ban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await interaction.guild.ban(kullanici, reason=f"{sebep} | {interaction.user}")
        embed = discord.Embed(title="🔨 BAN", description=f"{kullanici.mention} banlandı.\n**Sebep:** {sebep}", color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="kick", description="Kick atar (Guard/Cmds)")
async def kick(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await kullanici.kick(reason=f"{sebep} | {interaction.user}")
        embed = discord.Embed(title="👢 KICK", description=f"{kullanici.mention} atıldı.\n**Sebep:** {sebep}", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="uyari", description="Uyarı verir (Guard/Cmds)")
async def uyari(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO uyarilar (user_id, sebep, yetkili_id, tarih) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, interaction.user.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="⚠️ UYARI", description=f"{kullanici.mention} uyarıldı.\n**Sebep:** {sebep}", color=discord.Color.yellow())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="uyarilar", description="Uyarıları gösterir")
async def uyarilar(interaction: discord.Interaction, kullanici: discord.Member):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sebep FROM uyarilar WHERE user_id = ?", (kullanici.id,))
    kayitlar = c.fetchall()
    conn.close()
    if not kayitlar:
        await interaction.response.send_message(f"{kullanici.mention} uyarısı yok.", ephemeral=True)
        return
    mesaj = "\n".join([f"• {sebep}" for (sebep,) in kayitlar])
    await interaction.response.send_message(embed=discord.Embed(title=f"⚠️ {kullanici.display_name} Uyarıları", description=mesaj, color=discord.Color.orange()))

# ========================================
# İSTATİSTİK
# ========================================

@bot.tree.command(name="profil", description="Profil gösterir")
async def profil(interaction: discord.Interaction, kullanici: discord.Member = None):
    if kullanici is None:
        kullanici = interaction.user
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT mesaj, seviye, xp FROM uyeler WHERE user_id = ?", (kullanici.id,))
    kayit = c.fetchone()
    conn.close()
    mesaj = kayit[0] if kayit else 0
    seviye = kayit[1] if kayit else 1
    xp = kayit[2] if kayit else 0
    embed = discord.Embed(title=f"👤 {kullanici.display_name}", color=discord.Color.blue())
    if kullanici.avatar:
        embed.set_thumbnail(url=kullanici.avatar.url)
    embed.add_field(name="Mesaj", value=mesaj)
    embed.add_field(name="Seviye", value=seviye)
    embed.add_field(name="XP", value=xp)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="seviye", description="Seviyeni gösterir")
async def seviye(interaction: discord.Interaction):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT mesaj, seviye, xp FROM uyeler WHERE user_id = ?", (interaction.user.id,))
    kayit = c.fetchone()
    conn.close()
    mesaj = kayit[0] if kayit else 0
    seviye = kayit[1] if kayit else 1
    xp = kayit[2] if kayit else 0
    await interaction.response.send_message(f"⭐ Seviye: **{seviye}** | XP: **{xp}** | Mesaj: **{mesaj}**")


@bot.tree.command(name="liderlik", description="En aktifler")
async def liderlik(interaction: discord.Interaction):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT user_id, mesaj FROM uyeler ORDER BY mesaj DESC LIMIT 10")
    kayitlar = c.fetchall()
    conn.close()
    mesaj = ""
    for i, (uid, msj) in enumerate(kayitlar, 1):
        uye = interaction.guild.get_member(uid)
        isim = uye.display_name if uye else f"ID: {uid}"
        mesaj += f"**{i}.** {isim} - {msj}\n"
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Liderlik", description=mesaj, color=discord.Color.gold()))

# ========================================
# EĞLENCE
# ========================================

@bot.tree.command(name="zar", description="Zar atar")
async def zar(interaction: discord.Interaction):
    await interaction.response.send_message(f"🎲 **{random.randint(1, 6)}**")

@bot.tree.command(name="yazitura", description="Yazı tura")
async def yazitura(interaction: discord.Interaction):
    await interaction.response.send_message(f"🪙 **{random.choice(['Yazı', 'Tura'])}**")

@bot.tree.command(name="espri", description="Espri yapar")
async def espri(interaction: discord.Interaction):
    await interaction.response.send_message(f"😂 {random.choice(['Sinüsleri var.', 'Antivirüs var.', 'Bug var.'])}")

# ========================================
# YÖNETİM
# ========================================

@bot.tree.command(name="duyuru", description="Duyuru atar (Admin)")
@app_commands.default_permissions(administrator=True)
async def duyuru(interaction: discord.Interaction, baslik: str, mesaj: str):
    embed = discord.Embed(title=f"📢 {baslik}", description=mesaj, color=discord.Color.red())
    await interaction.channel.send("@everyone", embed=embed)
    await interaction.response.send_message("✅ Duyuru atıldı.", ephemeral=True)


@bot.tree.command(name="anket", description="Anket (Admin)")
@app_commands.default_permissions(administrator=True)
async def anket(interaction: discord.Interaction, soru: str):
    embed = discord.Embed(title="📊 ANKET", description=soru, color=discord.Color.blue())
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await interaction.response.send_message("✅ Anket kuruldu.", ephemeral=True)

# ========================================
# BAŞLATMA
# ========================================

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ Token yok")
