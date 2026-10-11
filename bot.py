import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import sqlite3
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
# BOT AYARLARI
# ========================================

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ========================================
# YETKİLİ ROLLER
# ========================================

YETKILI_ROLLER = ["Guard", "/Cmds", "Vise Team"]
MOD_ROLLER = ["Guard", "/Cmds"]
TICKET_ROLLER = ["Vise Team", "Guard"]
KAYIT_YETKILI_ROLLER = ["Guard", "/Cmds", "Vise Team"]

# ========================================
# VERİTABANI
# ========================================

DB = "sancak_rp.db"

def db_kur():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS uyeler
                 (user_id INTEGER PRIMARY KEY, mesaj INTEGER DEFAULT 0, xp INTEGER DEFAULT 0,
                  seviye INTEGER DEFAULT 1, son_gunluk TEXT, uyari INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (kanal_id INTEGER PRIMARY KEY, kullanici_id INTEGER, konu TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ipbanlar
                 (user_id INTEGER PRIMARY KEY, sebep TEXT, tarih TEXT, yetkili_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS uyarilar
                 (user_id INTEGER, sebep TEXT, yetkili_id INTEGER, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS loglar
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tip TEXT, kullanici_id INTEGER, aciklama TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS karakterler
                 (user_id INTEGER PRIMARY KEY, isim TEXT, yas INTEGER, meslek TEXT, hikaye TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS arac_kayit
                 (user_id INTEGER PRIMARY KEY, plaka TEXT, marka TEXT, model TEXT, renk TEXT, sahiplik TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS is_basvuru
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, is_turu TEXT, icerik TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ehliyet
                 (user_id INTEGER PRIMARY KEY, isim TEXT, yas TEXT, ehliyet_turu TEXT, deneyim TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS silah
                 (user_id INTEGER PRIMARY KEY, isim TEXT, silah_turu TEXT, neden TEXT, gecmis TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ev
                 (user_id INTEGER PRIMARY KEY, isim TEXT, ev_adresi TEXT, ev_turu TEXT, fiyat TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sikayet
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, sikayet_edilen TEXT, sebep TEXT, kanit TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS istek_oneri
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tip TEXT, baslik TEXT, icerik TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ayarlar
                 (anahtar TEXT PRIMARY KEY, deger TEXT)''')
    conn.commit()
    conn.close()

db_kur()

def db_baglan():
    return sqlite3.connect(DB)

def ayar_al(anahtar, varsayilan=None):
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT deger FROM ayarlar WHERE anahtar = ?", (anahtar,))
    kayit = c.fetchone()
    conn.close()
    return kayit[0] if kayit else varsayilan

def ayar_koy(anahtar, deger):
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO ayarlar (anahtar, deger) VALUES (?, ?)", (anahtar, str(deger)))
    conn.commit()
    conn.close()

# ========================================
# YARDIMCI
# ========================================

def yetkili_mi(member, roller):
    return any(r.name in roller for r in member.roles)

def embed_yap(baslik, aciklama, renk=discord.Color.blue()):
    return discord.Embed(title=baslik, description=aciklama, color=renk, timestamp=datetime.now())

async def banner_gonder(kanal, embed, view):
    if os.path.exists("banner.png"):
        file = discord.File("banner.png", filename="banner.png")
        embed.set_image(url="attachment://banner.png")
        await kanal.send(file=file, embed=embed, view=view)
    else:
        await kanal.send(embed=embed, view=view)

# ========================================
# HAZIR
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

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT INTO uyeler (user_id, mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET mesaj = mesaj + 1", (message.author.id,))
    c.execute("SELECT mesaj, xp, seviye FROM uyeler WHERE user_id = ?", (message.author.id,))
    kayit = c.fetchone()
    if kayit:
        mesaj_s, xp, seviye = kayit
        yeni_xp = xp + random.randint(5, 15)
        yeni_seviye = mesaj_s // 50 + 1
        c.execute("UPDATE uyeler SET xp = ?, seviye = ? WHERE user_id = ?", (yeni_xp, yeni_seviye, message.author.id))
        if yeni_seviye > seviye:
            try:
                await message.channel.send(f"🎉 {message.author.mention} **{yeni_seviye}. seviyeye** ulaştı!")
            except:
                pass
    conn.commit()
    conn.close()
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    try:
        embed = discord.Embed(
            title="👋 Sancak Roleplay'e Hoş Geldin!",
            description=f"Merhaba **{member.display_name}**,\n\n"
                        f"**{member.guild.name}** sunucumuza hoş geldin!\n\n"
                        f"Rol yapmaya başlamadan önce kayıt olman gerekiyor.\n\n"
                        f"📝 Kayıt olmak için sunucudaki **kayıt kanalına** git, "
                        f"**Kayıt Ol** butonuna tıkla ve formu doldur.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sancak Roleplay • Kayıt Sistemi")
        await member.send(embed=embed)
    except:
        pass

# ========================================
# YARDIM
# ========================================

@bot.tree.command(name="yardim", description="Sancak RP Botu yardım menüsü")
async def yardim(interaction: discord.Interaction):
    embed = discord.Embed(title="🎯 Sancak RP Botu", description="Kullanılabilir komutlar:", color=discord.Color.blue())
    embed.add_field(name="📝 Kayıt Sistemleri", value="`/kayitkur` `/karakterkur` `/arackur` `/iskur` `/ehliyetkur` `/silahkur` `/evkur` `/sikayetkur` `/yetkilikur` `/istekkur`", inline=False)
    embed.add_field(name="⚙️ Ayar Komutları", value="`/kayit_ayar` `/karakter_ayar` `/arac_ayar` `/is_ayar` `/ehliyet_ayar` `/silah_ayar` `/ev_ayar` `/sikayet_ayar` `/yetkili_ayar` `/istek_ayar`", inline=False)
    embed.add_field(name="🎫 Ticket", value="`/ticketkur`", inline=False)
    embed.add_field(name="🎭 Rol Sistemi", value="`/rolver` `/rolal` `/toplurol`", inline=False)
    embed.add_field(name="⚖️ Moderasyon", value="`/ban` `/kick` `/ipban` `/unban` `/timeout` `/untimeout` `/uyari` `/uyarilar`", inline=False)
    embed.add_field(name="📊 İstatistik", value="`/profil` `/liderlik` `/gunluk`", inline=False)
    embed.add_field(name="🎉 Etkinlik", value="`/cekiliş` `/anket` `/duyuru`", inline=False)
    embed.add_field(name="⚙️ Yönetim", value="`/log_kanal` `/ticket_kategori` `/ayarlar`", inline=False)
    embed.add_field(name="🎲 Eğlence", value="`/zar` `/yazitura` `/espri`", inline=False)
    embed.set_footer(text="Sancak Roleplay • Destek Sistemi")
    await interaction.response.send_message(embed=embed)

# ========================================
# 1. WHITELIST KAYIT
# ========================================

class KayitFormu(discord.ui.Modal, title="Sancak Roleplay - Whitelist Başvuru"):
    soru1 = discord.ui.TextInput(label="1. Adınız, Yaşınız ve Bizi Nereden Buldunuz?", style=discord.TextStyle.short, required=True)
    soru2 = discord.ui.TextInput(label="2. Meta Gaming ve Fail RP Nedir?", style=discord.TextStyle.paragraph, required=True)
    soru3 = discord.ui.TextInput(label="3. IC ve OOC Nedir?", style=discord.TextStyle.paragraph, required=True)
    soru4 = discord.ui.TextInput(label="4. VDM ve RDM Nedir?", style=discord.TextStyle.paragraph, required=True)
    soru5 = discord.ui.TextInput(label="5. Örnek Kaza Rolü (/me ve /do)", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("kayit_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log kanalı ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log kanalı yok!", ephemeral=True)
            return
        embed = discord.Embed(title="📝 Sancak Roleplay - Whitelist",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.blue())
        embed.add_field(name="1. Ad, Yaş, Kaynak", value=self.soru1.value[:1024], inline=False)
        embed.add_field(name="2. MG & Fail RP", value=self.soru2.value[:1024], inline=False)
        embed.add_field(name="3. IC & OOC", value=self.soru3.value[:1024], inline=False)
        embed.add_field(name="4. VDM & RDM", value=self.soru4.value[:1024], inline=False)
        embed.add_field(name="5. Örnek Kaza", value=self.soru5.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Whitelist")
        await log.send(embed=embed, view=KayitOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class KayitOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        if not uye:
            await interaction.response.send_message("❌ Kullanıcı yok.", ephemeral=True)
            return
        rid = ayar_al("kayit_verilecek_rol")
        try:
            if rid:
                r = interaction.guild.get_role(int(rid))
                if r:
                    await uye.add_roles(r)
            await uye.send("🎉 Tebrikler! Sancak Roleplay kaydınız kabul edildi.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message(f"✅ {uye.mention} onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("Üzgünüz, Sancak Roleplay başvurunuz reddedildi.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class KayitPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, emoji="➕", custom_id="kayit_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(KayitFormu())


@bot.tree.command(name="kayitkur", description="Kayıt panelini kurar")
@app_commands.default_permissions(administrator=True)
async def kayitkur(interaction):
    embed = discord.Embed(
        title="🎫 SANCAK ROLEPLAY KAYIT SİSTEMİ",
        description="**Hoş Geldiniz!**\n\nSunucumuza katılmak için kayıt başvurusunda bulunmanız gerekmektedir.\n\nAşağıdaki buton aracılığıyla formu doldurabilirsiniz.",
        color=discord.Color.from_rgb(0, 102, 204)
    )
    embed.add_field(name="⚠️ Unutmayın", value="• Başvurunuz 24 saat içinde incelenir.\n• Yanlış bilgi verenler reddedilir.\n• Sonuç DM'den bildirilir.", inline=False)
    embed.set_footer(text="Sancak Roleplay • Whitelist", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, KayitPaneli())
    await interaction.response.send_message("✅ Kayıt paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="kayit_ayar", description="Kayıt sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def kayit_ayar(interaction, log_kanal: discord.TextChannel, verilecek_rol: discord.Role):
    ayar_koy("kayit_log_kanal", log_kanal.id)
    ayar_koy("kayit_verilecek_rol", verilecek_rol.id)
    await interaction.response.send_message("✅ Kayıt sistemi ayarlandı.", ephemeral=True)

# ========================================
# 2. KARAKTER KAYIT
# ========================================

class KarakterFormu(discord.ui.Modal, title="Sancak Roleplay - Karakter Kayıt"):
    isim = discord.ui.TextInput(label="Karakter İsmi", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Karakter Yaşı", style=discord.TextStyle.short, required=True)
    meslek = discord.ui.TextInput(label="Karakter Mesleği", style=discord.TextStyle.short, required=True)
    hikaye = discord.ui.TextInput(label="Karakter Hikayesi", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("karakter_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO karakterler (user_id, isim, yas, meslek, hikaye, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, int(self.yas.value) if self.yas.value.isdigit() else 0, self.meslek.value, self.hikaye.value, "beklemede", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="📝 Sancak Roleplay - Karakter Kaydı",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.purple())
        embed.add_field(name="İsim", value=self.isim.value, inline=False)
        embed.add_field(name="Yaş", value=self.yas.value, inline=True)
        embed.add_field(name="Meslek", value=self.meslek.value, inline=True)
        embed.add_field(name="Hikaye", value=self.hikaye.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Karakter")
        await log.send(embed=embed, view=KarakterOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class KarakterOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE karakterler SET durum='onaylandi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 Karakter kaydınız onaylandı!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE karakterler SET durum='reddedildi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("Üzgünüz, karakter kaydınız reddedildi.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class KarakterPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Karakter Kaydı Yap", style=discord.ButtonStyle.primary, emoji="📝", custom_id="karakter_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(KarakterFormu())


@bot.tree.command(name="karakterkur", description="Karakter panelini kurar")
@app_commands.default_permissions(administrator=True)
async def karakterkur(interaction):
    embed = discord.Embed(
        title="🎮 SANCAK ROLEPLAY KARAKTER KAYIT",
        description="**Karakter Kaydı**\n\nRol yapmaya başlamadan önce karakterinizi oluşturun.",
        color=discord.Color.purple()
    )
    embed.add_field(name="⚠️ Unutmayın", value="• İsim RP kurallarına uygun olmalı.\n• Hikaye en az 3-4 cümle olmalı.", inline=False)
    embed.set_footer(text="Sancak Roleplay • Karakter", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, KarakterPaneli())
    await interaction.response.send_message("✅ Karakter paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="karakter_ayar", description="Karakter sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def karakter_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("karakter_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Karakter log ayarlandı.", ephemeral=True)


@bot.tree.command(name="karakter_bilgi", description="Karakter bilgisi")
async def karakter_bilgi(interaction, kullanici: discord.Member = None):
    if kullanici is None:
        kullanici = interaction.user
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT isim, yas, meslek, hikaye, durum FROM karakterler WHERE user_id=?", (kullanici.id,))
    k = c.fetchone()
    conn.close()
    if not k:
        await interaction.response.send_message(f"{kullanici.mention} karakter kaydı yok.", ephemeral=True)
        return
    embed = discord.Embed(title=f"🎮 {kullanici.display_name} Karakter", color=discord.Color.purple())
    embed.add_field(name="İsim", value=k[0])
    embed.add_field(name="Yaş", value=k[1])
    embed.add_field(name="Meslek", value=k[2])
    embed.add_field(name="Durum", value=k[4])
    embed.add_field(name="Hikaye", value=k[3][:1024], inline=False)
    await interaction.response.send_message(embed=embed)

# ========================================
# 3. ARAÇ KAYIT
# ========================================

class AracFormu(discord.ui.Modal, title="Sancak Roleplay - Araç Kayıt"):
    plaka = discord.ui.TextInput(label="Plaka", style=discord.TextStyle.short, required=True)
    marka = discord.ui.TextInput(label="Marka", style=discord.TextStyle.short, required=True)
    model = discord.ui.TextInput(label="Model", style=discord.TextStyle.short, required=True)
    renk = discord.ui.TextInput(label="Renk", style=discord.TextStyle.short, required=True)
    sahiplik = discord.ui.TextInput(label="Aracın Size Ait Olduğunu Belirtin", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("arac_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO arac_kayit (user_id, plaka, marka, model, renk, sahiplik, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.plaka.value, self.marka.value, self.model.value, self.renk.value, self.sahiplik.value, "beklemede", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="🚗 Sancak Roleplay - Araç Kaydı",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.dark_blue())
        embed.add_field(name="Plaka", value=self.plaka.value, inline=True)
        embed.add_field(name="Marka", value=self.marka.value, inline=True)
        embed.add_field(name="Model", value=self.model.value, inline=True)
        embed.add_field(name="Renk", value=self.renk.value, inline=True)
        embed.add_field(name="Sahiplik", value=self.sahiplik.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Araç")
        await log.send(embed=embed, view=AracOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class AracOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE arac_kayit SET durum='onaylandi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 Araç kaydınız onaylandı!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE arac_kayit SET durum='reddedildi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class AracPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Araç Kaydı Yap", style=discord.ButtonStyle.primary, emoji="🚗", custom_id="arac_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(AracFormu())


@bot.tree.command(name="arackur", description="Araç panelini kurar")
@app_commands.default_permissions(administrator=True)
async def arackur(interaction):
    embed = discord.Embed(
        title="🚗 SANCAK ROLEPLAY ARAÇ KAYIT",
        description="**Araç Kaydı**\n\nAraçlarınızı kaydetmek için butona tıklayın.",
        color=discord.Color.dark_blue()
    )
    embed.add_field(name="⚠️ Unutmayın", value="• Çalıntı araç kaydı yasaktır.\n• Plaka RP kurallarına uygun olmalı.", inline=False)
    embed.set_footer(text="Sancak Roleplay • Araç", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, AracPaneli())
    await interaction.response.send_message("✅ Araç paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="arac_ayar", description="Araç sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def arac_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("arac_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Araç log ayarlandı.", ephemeral=True)

# ========================================
# 4. İŞ BAŞVURU
# ========================================

class IsFormu(discord.ui.Modal, title="Sancak Roleplay - İş Başvurusu"):
    is_turu = discord.ui.TextInput(label="İş Türü", style=discord.TextStyle.short, placeholder="Polis / Mafya / Doktor", required=True)
    isim = discord.ui.TextInput(label="Karakter İsminiz", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Karakter Yaşınız", style=discord.TextStyle.short, required=True)
    deneyim = discord.ui.TextInput(label="Deneyiminiz", style=discord.TextStyle.paragraph, required=True)
    neden = discord.ui.TextInput(label="Neden Bu İşi İstiyorsunuz?", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("is_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        icerik = f"İsim: {self.isim.value}\nYaş: {self.yas.value}\nDeneyim: {self.deneyim.value}\nNeden: {self.neden.value}"
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT INTO is_basvuru (user_id, is_turu, icerik, durum, tarih) VALUES (?, ?, ?, 'beklemede', ?)",
                  (interaction.user.id, self.is_turu.value, icerik, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="💼 Sancak Roleplay - İş Başvurusu",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.orange())
        embed.add_field(name="İş Türü", value=self.is_turu.value, inline=False)
        embed.add_field(name="İsim", value=self.isim.value, inline=True)
        embed.add_field(name="Yaş", value=self.yas.value, inline=True)
        embed.add_field(name="Deneyim", value=self.deneyim.value[:1024], inline=False)
        embed.add_field(name="Neden", value=self.neden.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • İş")
        await log.send(embed=embed, view=IsOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class IsOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 İş başvurunuz onaylandı!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class IsPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="İş Başvurusu Yap", style=discord.ButtonStyle.primary, emoji="💼", custom_id="is_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(IsFormu())


@bot.tree.command(name="iskur", description="İş panelini kurar")
@app_commands.default_permissions(administrator=True)
async def iskur(interaction):
    embed = discord.Embed(
        title="💼 SANCAK ROLEPLAY İŞ BAŞVURU",
        description="**İş Başvurusu**\n\nBir işe başvurmak için butona tıklayın.",
        color=discord.Color.orange()
    )
    embed.add_field(name="📋 Mevcut İşler", value="• 👮 Polis\n• 🚑 Doktor\n• 🔧 Teknik\n• 🕵️ Mafya", inline=False)
    embed.set_footer(text="Sancak Roleplay • İş", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, IsPaneli())
    await interaction.response.send_message("✅ İş paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="is_ayar", description="İş sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def is_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("is_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ İş log ayarlandı.", ephemeral=True)

# ========================================
# 5. EHLİYET
# ========================================

class EhliyetFormu(discord.ui.Modal, title="Sancak Roleplay - Ehliyet"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Yaş", style=discord.TextStyle.short, required=True)
    ehliyet_turu = discord.ui.TextInput(label="Ehliyet Türü", style=discord.TextStyle.short, placeholder="A / B / C", required=True)
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("ehliyet_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ehliyet (user_id, isim, yas, ehliyet_turu, deneyim, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, self.yas.value, self.ehliyet_turu.value, self.deneyim.value, "beklemede", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="🪪 Sancak Roleplay - Ehliyet",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.teal())
        embed.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        embed.add_field(name="Yaş", value=self.yas.value, inline=True)
        embed.add_field(name="Tür", value=self.ehliyet_turu.value, inline=True)
        embed.add_field(name="Deneyim", value=self.deneyim.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Ehliyet")
        await log.send(embed=embed, view=EhliyetOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class EhliyetOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE ehliyet SET durum='onaylandi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 Ehliyet başvurunuz onaylandı!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class EhliyetPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ehliyet Başvurusu", style=discord.ButtonStyle.primary, emoji="🪪", custom_id="ehliyet_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(EhliyetFormu())


@bot.tree.command(name="ehliyetkur", description="Ehliyet panelini kurar")
@app_commands.default_permissions(administrator=True)
async def ehliyetkur(interaction):
    embed = discord.Embed(title="🪪 SANCAK ROLEPLAY EHLİYET",
                          description="**Ehliyet Başvurusu**\n\nAraç kullanmak için ehliyet başvurusu yapın.",
                          color=discord.Color.teal())
    embed.add_field(name="📋 Türler", value="• 🏍️ A - Motosiklet\n• 🚗 B - Otomobil\n• 🚚 C - Kamyon", inline=False)
    embed.set_footer(text="Sancak Roleplay • Ehliyet", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, EhliyetPaneli())
    await interaction.response.send_message("✅ Ehliyet paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="ehliyet_ayar", description="Ehliyet sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def ehliyet_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("ehliyet_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ehliyet log ayarlandı.", ephemeral=True)

# ========================================
# 6. SİLAH RUHSATI
# ========================================

class SilahFormu(discord.ui.Modal, title="Sancak Roleplay - Silah Ruhsatı"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    silah_turu = discord.ui.TextInput(label="Silah Türü", style=discord.TextStyle.short, required=True)
    neden = discord.ui.TextInput(label="Neden Ruhsat?", style=discord.TextStyle.paragraph, required=True)
    gecmis = discord.ui.TextInput(label="Sabıka Kaydınız?", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("silah_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO silah (user_id, isim, silah_turu, neden, gecmis, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, self.silah_turu.value, self.neden.value, self.gecmis.value, "beklemede", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="🔫 Sancak Roleplay - Silah Ruhsatı",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.dark_red())
        embed.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        embed.add_field(name="Silah", value=self.silah_turu.value, inline=True)
        embed.add_field(name="Sabıka", value=self.gecmis.value, inline=True)
        embed.add_field(name="Neden", value=self.neden.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Silah")
        await log.send(embed=embed, view=SilahOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class SilahOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE silah SET durum='onaylandi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 Silah ruhsatı başvurunuz onaylandı!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class SilahPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Silah Ruhsatı", style=discord.ButtonStyle.primary, emoji="🔫", custom_id="silah_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(SilahFormu())


@bot.tree.command(name="silahkur", description="Silah panelini kurar")
@app_commands.default_permissions(administrator=True)
async def silahkur(interaction):
    embed = discord.Embed(title="🔫 SANCAK ROLEPLAY SİLAH RUHSATI",
                          description="**Silah Ruhsatı**\n\nSilah taşımak için ruhsat başvurusu yapın.",
                          color=discord.Color.dark_red())
    embed.add_field(name="⚠️ Unutmayın", value="• Ruhsatsız silah yasaktır.\n• Sabıka kaydı olanlar başvuramaz.", inline=False)
    embed.set_footer(text="Sancak Roleplay • Silah", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, SilahPaneli())
    await interaction.response.send_message("✅ Silah paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="silah_ayar", description="Silah sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def silah_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("silah_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Silah log ayarlandı.", ephemeral=True)

# ========================================
# 7. EV KAYIT
# ========================================

class EvFormu(discord.ui.Modal, title="Sancak Roleplay - Ev Kaydı"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    ev_adresi = discord.ui.TextInput(label="Ev Adresi", style=discord.TextStyle.short, required=True)
    ev_turu = discord.ui.TextInput(label="Ev Türü", style=discord.TextStyle.short, placeholder="Daire / Villa", required=True)
    fiyat = discord.ui.TextInput(label="Ödenen Fiyat", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("ev_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ev (user_id, isim, ev_adresi, ev_turu, fiyat, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, self.ev_adresi.value, self.ev_turu.value, self.fiyat.value, "beklemede", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="🏠 Sancak Roleplay - Ev Kaydı",
                              description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.green())
        embed.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        embed.add_field(name="Adres", value=self.ev_adresi.value, inline=True)
        embed.add_field(name="Tür", value=self.ev_turu.value, inline=True)
        embed.add_field(name="Fiyat", value=self.fiyat.value, inline=True)
        embed.set_footer(text="Sancak Roleplay • Ev")
        await log.send(embed=embed, view=EvOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class EvOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE ev SET durum='onaylandi' WHERE user_id=?", (self.uid,))
        conn.commit()
        conn.close()
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 Ev kaydınız onaylandı!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Onaylandı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class EvPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ev Kaydı Yap", style=discord.ButtonStyle.primary, emoji="🏠", custom_id="ev_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(EvFormu())


@bot.tree.command(name="evkur", description="Ev panelini kurar")
@app_commands.default_permissions(administrator=True)
async def evkur(interaction):
    embed = discord.Embed(title="🏠 SANCAK ROLEPLAY EV KAYIT",
                          description="**Ev Kaydı**\n\nEv satın aldıysanız kaydınızı yapın.",
                          color=discord.Color.green())
    embed.add_field(name="📋 Ev Türleri", value="• 🏢 Daire\n• 🏡 Villa\n• 🏘️ Müstakil", inline=False)
    embed.set_footer(text="Sancak Roleplay • Ev", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, EvPaneli())
    await interaction.response.send_message("✅ Ev paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="ev_ayar", description="Ev sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def ev_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("ev_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ev log ayarlandı.", ephemeral=True)

# ========================================
# 8. ŞİKAYET
# ========================================

class SikayetFormu(discord.ui.Modal, title="Sancak Roleplay - Şikayet"):
    sikayet_edilen = discord.ui.TextInput(label="Şikayet Edilen", style=discord.TextStyle.short, required=True)
    sebep = discord.ui.TextInput(label="Şikayet Sebebi", style=discord.TextStyle.paragraph, required=True)
    kanit = discord.ui.TextInput(label="Kanıtınız Var mı?", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction):
        log_id = ayar_al("sikayet_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT INTO sikayet (user_id, sikayet_edilen, sebep, kanit, durum, tarih) VALUES (?, ?, ?, ?, 'beklemede', ?)",
                  (interaction.user.id, self.sikayet_edilen.value, self.sebep.value, self.kanit.value or "", datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title="⚖️ Sancak Roleplay - Şikayet",
                              description=f"**Şikayet Eden:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.dark_orange())
        embed.add_field(name="Şikayet Edilen", value=self.sikayet_edilen.value, inline=False)
        embed.add_field(name="Sebep", value=self.sebep.value[:1024], inline=False)
        embed.add_field(name="Kanıt", value=(self.kanit.value or "Yok")[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Şikayet")
        await log.send(embed=embed, view=SikayetOnay(interaction.user.id))
        await interaction.response.send_message("✅ Şikayetiniz alındı!", ephemeral=True)


class SikayetOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="İşleme Al", style=discord.ButtonStyle.success, emoji="✅")
    async def islem(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("🎉 Şikayetiniz işleme alındı.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ İşleme Alan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ İşleme alındı.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class SikayetPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Şikayet Oluştur", style=discord.ButtonStyle.primary, emoji="⚖️", custom_id="sikayet_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(SikayetFormu())


@bot.tree.command(name="sikayetkur", description="Şikayet panelini kurar")
@app_commands.default_permissions(administrator=True)
async def sikayetkur(interaction):
    embed = discord.Embed(title="⚖️ SANCAK ROLEPLAY ŞİKAYET",
                          description="**Şikayet Sistemi**\n\nBir kullanıcıdan şikayetçiyseniz butona tıklayın.",
                          color=discord.Color.dark_orange())
    embed.add_field(name="⚠️ Unutmayın", value="• Sahte şikayet kalıcı ban sebebidir.\n• Kanıtsız şikayet reddedilir.", inline=False)
    embed.set_footer(text="Sancak Roleplay • Şikayet", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, SikayetPaneli())
    await interaction.response.send_message("✅ Şikayet paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="sikayet_ayar", description="Şikayet sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def sikayet_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("sikayet_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Şikayet log ayarlandı.", ephemeral=True)

# ========================================
# 9. YETKİLİ BAŞVURU (YENİ)
# ========================================

class YetkiliFormu(discord.ui.Modal, title="Sancak Roleplay - Yetkili Başvuru"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Yaşınız", style=discord.TextStyle.short, required=True)
    deneyim = discord.ui.TextInput(label="Daha Önce Yetkili Oldunuz mu?", style=discord.TextStyle.paragraph, placeholder="Hangi sunucularda, ne kadar süre?", required=True)
    neden = discord.ui.TextInput(label="Neden Yetkili Olmak İstiyorsunuz?", style=discord.TextStyle.paragraph, required=True)
    gunluk_sure = discord.ui.TextInput(label="Günde Kaç Saat Aktif Olabilirsiniz?", style=discord.TextStyle.short, placeholder="Örnek: 4-5 saat", required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("yetkili_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        embed = discord.Embed(title="🛡️ Sancak Roleplay - Yetkili Başvurusu",
                              description=f"**Başvuran:** {interaction.user.mention} (`{interaction.user.id}`)\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.from_rgb(0, 200, 255))
        embed.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        embed.add_field(name="Yaş", value=self.yas.value, inline=True)
        embed.add_field(name="Günlük Aktiflik", value=self.gunluk_sure.value, inline=True)
        embed.add_field(name="Deneyim", value=self.deneyim.value[:1024], inline=False)
        embed.add_field(name="Neden Yetkili?", value=self.neden.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Yetkili Başvuru")
        await log.send(embed=embed, view=YetkiliOnay(interaction.user.id))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)


class YetkiliOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success, emoji="✅")
    async def kabul(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        if not uye:
            await interaction.response.send_message("❌ Kullanıcı yok.", ephemeral=True)
            return
        rid = ayar_al("yetkili_verilecek_rol")
        try:
            if rid:
                r = interaction.guild.get_role(int(rid))
                if r:
                    await uye.add_roles(r)
            await uye.send("🎉 Tebrikler! Sancak Roleplay yetkili başvurunuz **KABUL EDİLDİ**. Yetkililerimiz sizinle iletişime geçecek.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Kabul Eden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message(f"✅ {uye.mention} yetkili olarak kabul edildi.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("Üzgünüz, Sancak Roleplay yetkili başvurunuz **REDDEDİLDİ**. İleride tekrar başvurabilirsiniz.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class YetkiliPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Yetkili Başvurusu Yap", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="yetkili_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(YetkiliFormu())


@bot.tree.command(name="yetkilikur", description="Yetkili başvuru panelini kurar")
@app_commands.default_permissions(administrator=True)
async def yetkilikur(interaction):
    embed = discord.Embed(
        title="🛡️ SANCAK ROLEPLAY YETKİLİ BAŞVURU SİSTEMİ",
        description="**Yetkili Başvurusu**\n\n"
                    "Sunucumuzda yetkili olmak için aşağıdaki butona tıklayarak başvuru formunu doldurabilirsiniz.\n\n"
                    "**Genel Kurallar:**\n"
                    "• Başvurunuz yetkili ekibimiz tarafından incelenecektir.\n"
                    "• Yanlış bilgi verenler kalıcı olarak reddedilir.\n"
                    "• Sonuç DM'den bildirilecektir.\n"
                    "• Başvurunuz 24 saat içinde sonuçlanır.",
        color=discord.Color.from_rgb(0, 200, 255)
    )
    embed.add_field(
        name="⚠️ Unutmayın",
        value="• En az 15 yaşında olmalısınız.\n"
              "• Günlük en az 2 saat aktif olmalısınız.\n"
              "• Daha önce yetkili olmuşsanız avantaj sağlar.\n"
              "• Sadece 1 kez başvuru yapabilirsiniz.",
        inline=False
    )
    embed.set_footer(text="Sancak Roleplay • Yetkili Başvuru Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, YetkiliPaneli())
    await interaction.response.send_message("✅ Yetkili başvuru paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="yetkili_ayar", description="Yetkili başvuru sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def yetkili_ayar(interaction, log_kanal: discord.TextChannel, verilecek_rol: discord.Role):
    ayar_koy("yetkili_log_kanal", log_kanal.id)
    ayar_koy("yetkili_verilecek_rol", verilecek_rol.id)
    embed = discord.Embed(
        title="✅ Yetkili Başvuru Sistemi Ayarlandı",
        description=f"**Log Kanalı:** {log_kanal.mention}\n**Verilecek Rol:** {verilecek_rol.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================================
# 10. İSTEK & ÖNERİ (YENİ)
# ========================================

class IstekFormu(discord.ui.Modal, title="Sancak Roleplay - İstek & Öneri"):
    tip = discord.ui.TextInput(label="Tip", style=discord.TextStyle.short, placeholder="İstek / Öneri / Şikayet", required=True)
    baslik = discord.ui.TextInput(label="Başlık", style=discord.TextStyle.short, required=True)
    icerik = discord.ui.TextInput(label="İçerik", style=discord.TextStyle.paragraph, placeholder="Detaylı açıklayın", required=True)

    async def on_submit(self, interaction):
        log_id = ayar_al("istek_log_kanal")
        if not log_id:
            await interaction.response.send_message("❌ Log ayarlanmamış!", ephemeral=True)
            return
        log = interaction.guild.get_channel(int(log_id))
        if not log:
            await interaction.response.send_message("❌ Log yok!", ephemeral=True)
            return
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT INTO istek_oneri (user_id, tip, baslik, icerik, durum, tarih) VALUES (?, ?, ?, ?, 'beklemede', ?)",
                  (interaction.user.id, self.tip.value, self.baslik.value, self.icerik.value, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        embed = discord.Embed(title=f"📩 Sancak Roleplay - {self.tip.value}",
                              description=f"**Gönderen:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                              color=discord.Color.from_rgb(255, 165, 0))
        embed.add_field(name="Başlık", value=self.baslik.value[:1024], inline=False)
        embed.add_field(name="İçerik", value=self.icerik.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • İstek & Öneri")
        await log.send(embed=embed, view=IstekOnay(interaction.user.id))
        await interaction.response.send_message("✅ Gönderiniz alındı! Teşekkür ederiz.", ephemeral=True)


class IstekOnay(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=None)
        self.uid = uid

    @discord.ui.button(label="Değerlendirildi", style=discord.ButtonStyle.success, emoji="✅")
    async def degerlendir(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("✅ Sancak Roleplay'e gönderdiğiniz istek/öneri **değerlendirildi**. İlginiz için teşekkürler!")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Değerlendiren: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("✅ Değerlendirildi olarak işaretlendi.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
            return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye:
                await uye.send("❌ Sancak Roleplay'e gönderdiğiniz istek/öneri **reddedildi**.")
        except:
            pass
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)


class IstekPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="İstek / Öneri Gönder", style=discord.ButtonStyle.primary, emoji="📩", custom_id="istek_btn")
    async def kayit(self, interaction, button):
        await interaction.response.send_modal(IstekFormu())


@bot.tree.command(name="istekkur", description="İstek & Öneri panelini kurar")
@app_commands.default_permissions(administrator=True)
async def istekkur(interaction):
    embed = discord.Embed(
        title="📩 SANCAK ROLEPLAY İSTEK & ÖNERİ SİSTEMİ",
        description="**İstek & Öneri Sistemi**\n\n"
                    "Sunucumuz için bir isteğiniz, öneriniz veya şikayetiniz mi var?\n\n"
                    "Aşağıdaki butona tıklayarak bize iletebilirsiniz. "
                    "Tüm görüşleriniz değerlendirilir ve size DM'den geri dönüş yapılır.\n\n"
                    "**Not:** Küfür, hakaret veya reklam içeren gönderiler direkt reddedilir.",
        color=discord.Color.from_rgb(255, 165, 0)
    )
    embed.add_field(
        name="💡 Neler İletebilirsiniz?",
        value="• 🎯 Sunucu için yeni fikirler\n"
              "• 🔧 Sistem önerileri\n"
              "• 🐛 Hata bildirimleri\n"
              "• 📢 Şikayetler",
        inline=False
    )
    embed.set_footer(text="Sancak Roleplay • İstek & Öneri Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, IstekPaneli())
    await interaction.response.send_message("✅ İstek & Öneri paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="istek_ayar", description="İstek & Öneri sistemini ayarlar")
@app_commands.default_permissions(administrator=True)
async def istek_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("istek_log_kanal", log_kanal.id)
    await interaction.response.send_message(f"✅ İstek & Öneri log kanalı {log_kanal.mention} olarak ayarlandı.", ephemeral=True)

# ========================================
# 11. TICKET
# ========================================

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Oyun İçi Destek", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="ticket_oyun")
    async def oyun(self, interaction, button):
        await ticket_ac(interaction, "Oyun İçi Destek")

    @discord.ui.button(label="Teknik Destek", style=discord.ButtonStyle.secondary, emoji="🔧", custom_id="ticket_teknik")
    async def teknik(self, interaction, button):
        await ticket_ac(interaction, "Teknik Destek")

    @discord.ui.button(label="Donate", style=discord.ButtonStyle.success, emoji="🛒", custom_id="ticket_donate")
    async def donate(self, interaction, button):
        await ticket_ac(interaction, "Donate")

    @discord.ui.button(label="AntiCheat", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="ticket_anticheat")
    async def anticheat(self, interaction, button):
        await ticket_ac(interaction, "AntiCheat")


async def ticket_ac(interaction, kategori):
    guild = interaction.guild
    user = interaction.user
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT kanal_id FROM tickets WHERE kullanici_id = ? AND durum = 'acik'", (user.id,))
    if c.fetchone():
        await interaction.response.send_message("❌ Zaten açık ticketın var!", ephemeral=True)
        conn.close()
        return
    kategori_id = ayar_al("ticket_kategori")
    kategori_kanal = guild.get_channel(int(kategori_id)) if kategori_id else None
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    for rol_ismi in TICKET_ROLLER:
        rol = discord.utils.get(guild.roles, name=rol_ismi)
        if rol:
            overwrites[rol] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    ticket_sayisi = len([k for k in guild.channels if k.name.startswith("ticket-")]) + 1
    kanal = await guild.create_text_channel(name=f"ticket-{ticket_sayisi:04d}", category=kategori_kanal, overwrites=overwrites)
    c.execute("INSERT INTO tickets (kanal_id, kullanici_id, konu, durum, tarih) VALUES (?, ?, ?, ?, ?)",
              (kanal.id, user.id, kategori, "acik", datetime.now().isoformat()))
    conn.commit()
    conn.close()
    embed = discord.Embed(title=f"🎫 Sancak RP Destek #{ticket_sayisi:04d}", description=f"{user.mention} - **{kategori}**", color=discord.Color.blue())
    await kanal.send(content=user.mention, embed=embed, view=TicketKontrol())
    await interaction.response.send_message(f"✅ Ticket: {kanal.mention}", ephemeral=True)


class TicketKontrol(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Çözüldü", style=discord.ButtonStyle.success, emoji="✅", custom_id="ticket_cozuldu")
    async def cozuldu(self, interaction, button):
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Çözüldü. Siliniyor...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_kapat")
    async def kapat(self, interaction, button):
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("🔒 Kapatılıyor...")
        await asyncio.sleep(3)
        await interaction.channel.delete()


@bot.tree.command(name="ticketkur", description="Ticket panelini kurar")
@app_commands.default_permissions(administrator=True)
async def ticketkur(interaction):
    embed = discord.Embed(
        title="🎫 SANCAK ROLEPLAY DESTEK SİSTEMİ",
        description="**Destek Talebi Oluştur**\n\nBilet oluşturmadan önce aşağıdaki kuralları okuyunuz.\n\n"
                    "**Genel Kurallar:**\n"
                    "• Biletinizi 24 saat içerisinde kontrol etmek zorundasınız.\n"
                    "• Yönetim üyelerine özel mesaj atmaktan kaçının.\n"
                    "• Sorunlarınızı bilet aracılığıyla iletin.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sancak Roleplay • Destek Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, embed, TicketPanel())
    await interaction.response.send_message("✅ Ticket paneli kuruldu.", ephemeral=True)

# ========================================
# 12. MODERASYON
# ========================================

@bot.tree.command(name="ban", description="Ban atar")
async def ban(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await interaction.guild.ban(kullanici, reason=f"{sebep} | {interaction.user}")
    await interaction.response.send_message(embed=embed_yap("🔨 BAN", f"{kullanici.mention} banlandı.\n**Sebep:** {sebep}", discord.Color.dark_red()))

@bot.tree.command(name="kick", description="Kick atar")
async def kick(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await kullanici.kick(reason=f"{sebep} | {interaction.user}")
    await interaction.response.send_message(embed=embed_yap("👢 KICK", f"{kullanici.mention} atıldı.\n**Sebep:** {sebep}", discord.Color.orange()))

@bot.tree.command(name="ipban", description="IP ban atar")
async def ipban(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await interaction.guild.ban(kullanici, reason=f"[IP BAN] {sebep} | {interaction.user}")
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO ipbanlar (user_id, sebep, tarih, yetkili_id) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, datetime.now().isoformat(), interaction.user.id))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=embed_yap("🚫 IP BAN", f"{kullanici.mention} IP banlandı.\n**Sebep:** {sebep}", discord.Color.dark_red()))

@bot.tree.command(name="unban", description="Ban kaldırır")
async def unban(interaction, kullanici_id: str):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(kullanici_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.mention} banı kaldırıldı.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Susturur")
async def timeout(interaction, kullanici: discord.Member, dakika: int, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await kullanici.timeout(timedelta(minutes=dakika), reason=sebep)
    await interaction.response.send_message(f"⏸️ {kullanici.mention} {dakika} dakika susturuldu.")

@bot.tree.command(name="untimeout", description="Susturmayı kaldırır")
async def untimeout(interaction, kullanici: discord.Member):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await kullanici.timeout(None)
    await interaction.response.send_message(f"▶️ {kullanici.mention} susturması kaldırıldı.")

@bot.tree.command(name="uyari", description="Uyarı verir (DM'li)")
async def uyari(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT INTO uyarilar (user_id, sebep, yetkili_id, tarih) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, interaction.user.id, datetime.now().isoformat()))
    c.execute("UPDATE uyeler SET uyari = uyari + 1 WHERE user_id = ?", (kullanici.id,))
    c.execute("SELECT COUNT(*) FROM uyarilar WHERE user_id = ?", (kullanici.id,))
    toplam = c.fetchone()[0]
    conn.commit()
    conn.close()
    # Kullanıcıya DM
    try:
        dm = discord.Embed(
            title="⚠️ UYARI ALDINIZ",
            description=f"**{interaction.guild.name}** sunucusunda uyarı aldınız.\n\n"
                        f"**Sebep:** {sebep}\n"
                        f"**Yetkili:** {interaction.user.display_name}\n"
                        f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                        f"**Toplam Uyarınız:** {toplam}",
            color=discord.Color.yellow()
        )
        dm.set_footer(text="Sancak Roleplay • Uyarı Sistemi")
        await kullanici.send(embed=dm)
        dm_durum = "✅ DM gönderildi"
    except:
        dm_durum = "❌ DM gönderilemedi (DM kapalı)"
    embed = discord.Embed(
        title="⚠️ UYARI VERİLDİ",
        description=f"**Kullanıcı:** {kullanici.mention}\n**Sebep:** {sebep}\n**Yetkili:** {interaction.user.mention}\n**Toplam:** {toplam}\n**DM:** {dm_durum}",
        color=discord.Color.yellow()
    )
    await interaction.response.send_message(embed=embed)
    log_id = ayar_al("log_kanal")
    if log_id:
        log = interaction.guild.get_channel(int(log_id))
        if log:
            try:
                await log.send(embed=embed)
            except:
                pass

@bot.tree.command(name="uyarilar", description="Uyarıları gösterir")
async def uyarilar(interaction, kullanici: discord.Member):
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT sebep, tarih FROM uyarilar WHERE user_id = ?", (kullanici.id,))
    kayitlar = c.fetchall()
    conn.close()
    if not kayitlar:
        await interaction.response.send_message(f"{kullanici.mention} uyarı yok.", ephemeral=True)
        return
    mesaj = "\n".join([f"• {s} ({t[:10]})" for s, t in kayitlar])
    await interaction.response.send_message(embed=embed_yap(f"⚠️ {kullanici.display_name}", mesaj, discord.Color.orange()))

# ========================================
# 13. ROL SİSTEMİ
# ========================================

@bot.tree.command(name="rolver", description="Rol verir")
async def rolver(interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await kullanici.add_roles(rol)
    await interaction.response.send_message(embed=embed_yap("🎭 ROL VERİLDİ", f"{kullanici.mention} → {rol.mention}", discord.Color.green()))

@bot.tree.command(name="rolal", description="Rol alır")
async def rolal(interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await kullanici.remove_roles(rol)
    await interaction.response.send_message(embed=embed_yap("🎭 ROL ALINDI", f"{kullanici.mention} ← {rol.mention}", discord.Color.red()))

@bot.tree.command(name="toplurol", description="Tüm üyelere rol verir")
async def toplurol(interaction, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await interaction.response.send_message(f"🎭 {rol.mention} veriliyor...", ephemeral=True)
    sayac = 0
    for uye in interaction.guild.members:
        if uye.bot: continue
        try:
            await uye.add_roles(rol)
            sayac += 1
            await asyncio.sleep(0.3)
        except: pass
    await interaction.channel.send(f"✅ {sayac} üyeye verildi.")

# ========================================
# 14. İSTATİSTİK
# ========================================

@bot.tree.command(name="profil", description="Profil gösterir")
async def profil(interaction, kullanici: discord.Member = None):
    if kullanici is None: kullanici = interaction.user
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT mesaj, xp, seviye, uyari FROM uyeler WHERE user_id = ?", (kullanici.id,))
    kayit = c.fetchone()
    conn.close()
    m, xp, sv, uy = kayit if kayit else (0, 0, 1, 0)
    embed = discord.Embed(title=f"👤 {kullanici.display_name}", color=discord.Color.blue())
    if kullanici.avatar: embed.set_thumbnail(url=kullanici.avatar.url)
    embed.add_field(name="📊 Mesaj", value=m)
    embed.add_field(name="⭐ Seviye", value=sv)
    embed.add_field(name="✨ XP", value=xp)
    embed.add_field(name="⚠️ Uyarı", value=uy)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="liderlik", description="En aktifler")
async def liderlik(interaction):
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT user_id, mesaj, seviye FROM uyeler ORDER BY mesaj DESC LIMIT 10")
    kayitlar = c.fetchall()
    conn.close()
    mesaj = ""
    for i, (uid, msj, sv) in enumerate(kayitlar, 1):
        uye = interaction.guild.get_member(uid)
        isim = uye.display_name if uye else f"ID: {uid}"
        mesaj += f"**{i}.** {isim} - {msj} mesaj (Seviye {sv})\n"
    await interaction.response.send_message(embed=embed_yap("🏆 Sancak RP Liderlik", mesaj, discord.Color.gold()))

@bot.tree.command(name="gunluk", description="Günlük ödül alır")
async def gunluk(interaction):
    conn = db_baglan()
    c = conn.cursor()
    bugun = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT son_gunluk FROM uyeler WHERE user_id = ?", (interaction.user.id,))
    kayit = c.fetchone()
    if kayit and kayit[0] == bugun:
        await interaction.response.send_message("⏳ Bugünkü ödülünü aldın!", ephemeral=True)
        conn.close()
        return
    odul = random.randint(50, 200)
    c.execute("INSERT INTO uyeler (user_id, xp, son_gunluk) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET xp = xp + ?, son_gunluk = ?",
              (interaction.user.id, odul, bugun, odul, bugun))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=embed_yap("🎁 GÜNLÜK ÖDÜL", f"**+{odul} XP** kazandın!", discord.Color.green()))

# ========================================
# 15. ETKİNLİK
# ========================================

@bot.tree.command(name="duyuru", description="Duyuru atar")
@app_commands.default_permissions(administrator=True)
async def duyuru(interaction, baslik: str, mesaj: str):
    embed = discord.Embed(title=f"📢 {baslik}", description=mesaj, color=discord.Color.red())
    embed.set_footer(text="Sancak RP • Duyuru")
    await interaction.channel.send("@everyone", embed=embed)
    await interaction.response.send_message("✅ Duyuru atıldı.", ephemeral=True)

@bot.tree.command(name="anket", description="Anket oluşturur")
@app_commands.default_permissions(administrator=True)
async def anket(interaction, soru: str):
    embed = discord.Embed(title="📊 Sancak RP Anket", description=soru, color=discord.Color.blue())
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await interaction.response.send_message("✅ Anket kuruldu.", ephemeral=True)

@bot.tree.command(name="cekiliş", description="Çekiliş başlatır")
@app_commands.default_permissions(administrator=True)
async def cekilis(interaction, odul: str, sure: int):
    embed = discord.Embed(title="🎉 SANCAK RP ÇEKİLİŞ!", description=f"**Ödül:** {odul}\n**Süre:** {sure} saniye\n🎉 emojisine tıkla!", color=discord.Color.gold())
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🎉")
    await interaction.response.send_message("✅ Çekiliş başladı.", ephemeral=True)
    await asyncio.sleep(sure)
    msg = await interaction.channel.fetch_message(msg.id)
    for reaction in msg.reactions:
        if str(reaction.emoji) == "🎉":
            kullanicilar = [u async for u in reaction.users() if not u.bot]
            if kullanicilar:
                kazanan = random.choice(kullanicilar)
                await interaction.channel.send(f"🎉 Tebrikler {kazanan.mention}! **{odul}** kazandın!")

# ========================================
# 16. YÖNETİM
# ========================================

@bot.tree.command(name="log_kanal", description="Log kanalı ayarlar")
@app_commands.default_permissions(administrator=True)
async def log_kanal(interaction, kanal: discord.TextChannel):
    ayar_koy("log_kanal", kanal.id)
    await interaction.response.send_message(f"✅ Log kanalı {kanal.mention}", ephemeral=True)

@bot.tree.command(name="ticket_kategori", description="Ticket kategori ayarlar")
@app_commands.default_permissions(administrator=True)
async def ticket_kategori(interaction, kategori: discord.CategoryChannel):
    ayar_koy("ticket_kategori", kategori.id)
    await interaction.response.send_message(f"✅ Ticket kategorisi {kategori.name}", ephemeral=True)

@bot.tree.command(name="ayarlar", description="Ayarları gösterir")
async def ayarlar(interaction):
    embed = discord.Embed(title="⚙️ Sancak RP Bot Ayarları", color=discord.Color.blue())
    for anahtar, isim in [
        ("log_kanal", "Log Kanalı"),
        ("ticket_kategori", "Ticket Kategorisi"),
        ("kayit_log_kanal", "Kayıt Log"),
        ("kayit_verilecek_rol", "Kayıt Rolü"),
        ("karakter_log_kanal", "Karakter Log"),
        ("arac_log_kanal", "Araç Log"),
        ("is_log_kanal", "İş Log"),
        ("ehliyet_log_kanal", "Ehliyet Log"),
        ("silah_log_kanal", "Silah Log"),
        ("ev_log_kanal", "Ev Log"),
        ("sikayet_log_kanal", "Şikayet Log"),
        ("yetkili_log_kanal", "Yetkili Log"),
        ("yetkili_verilecek_rol", "Yetkili Rolü"),
        ("istek_log_kanal", "İstek Log"),
    ]:
        deger = ayar_al(anahtar, "Ayarlanmadı")
        if deger != "Ayarlanmadı" and ("rol" in anahtar or "kategori" in anahtar):
            embed.add_field(name=isim, value=f"<@&{deger}>" if "rol" in anahtar else f"<#{deger}>", inline=True)
        elif deger != "Ayarlanmadı":
            embed.add_field(name=isim, value=f"<#{deger}>", inline=True)
        else:
            embed.add_field(name=isim, value=deger, inline=True)
    await interaction.response.send_message(embed=embed)

# ========================================
# 17. EĞLENCE
# ========================================

@bot.tree.command(name="zar", description="Zar atar")
async def zar(interaction):
    await interaction.response.send_message(f"🎲 **{random.randint(1, 6)}**")

@bot.tree.command(name="yazitura", description="Yazı tura")
async def yazitura(interaction):
    await interaction.response.send_message(f"🪙 **{random.choice(['Yazı', 'Tura'])}**")

@bot.tree.command(name="espri", description="Espri yapar")
async def espri(interaction):
    await interaction.response.send_message(f"😂 {random.choice(['Sinüsleri var.', 'Antivirüs var.', 'Bug var.'])}")

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
