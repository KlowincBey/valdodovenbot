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
                 (user_id INTEGER PRIMARY KEY, isim TEXT, yas INTEGER, meslek TEXT, hikaye TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS basvurular
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tip TEXT, icerik TEXT, durum TEXT, tarih TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ayarlar
                 (anahtar TEXT PRIMARY KEY, deger TEXT)''')
    conn.commit()
    conn.close()

db_kur()

def db_baglan():
    return sqlite3.connect(DB)

def log_ekle(tip, kullanici_id, aciklama):
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT INTO loglar (tip, kullanici_id, aciklama, tarih) VALUES (?, ?, ?, ?)",
              (tip, kullanici_id, aciklama, datetime.now().isoformat()))
    conn.commit()
    conn.close()

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

async def log_gonder(guild, tip, kullanici, aciklama):
    log_ekle(tip, kullanici.id, aciklama)
    kanal_id = ayar_al("log_kanal")
    if kanal_id:
        kanal = guild.get_channel(int(kanal_id))
        if kanal:
            embed = discord.Embed(
                title=f"📝 {tip}",
                description=f"**Kullanıcı:** {kullanici.mention}\n**Açıklama:** {aciklama}",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            try:
                await kanal.send(embed=embed)
            except:
                pass

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

# ========================================
# MESAJ & XP
# ========================================

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

# ========================================
# YENİ ÜYEYE DM
# ========================================

@bot.event
async def on_member_join(member):
    try:
        embed = discord.Embed(
            title="👋 Sunucuya Hoş Geldin!",
            description=f"Merhaba **{member.display_name}**,\n\n"
                        f"**{member.guild.name}** sunucumuza hoş geldin!\n\n"
                        f"Rol yapmaya başlamadan önce kayıt olman gerekiyor.\n\n"
                        f"📝 Kayıt olmak için **#kayıt** kanalına git, "
                        f"**Kayıt Ol** butonuna tıkla ve formu doldur.\n\n"
                        f"Başvurun onaylandığında sana bir rol verilecek ve rol yapmaya başlayabilirsin.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sancak Roleplay • Kayıt Sistemi")
        await member.send(embed=embed)
    except:
        pass

# ========================================
# SLASH: YARDIM
# ========================================

@bot.tree.command(name="yardim", description="Sancak RP Botu yardım menüsü")
async def yardim(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎯 Sancak RP Botu",
        description="Kullanılabilir komutlar:",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="🎫 Ticket", value="`/ticketkur`", inline=False)
    embed.add_field(name="📝 Kayıt", value="`/kayitkur` `/kayit_ayar`", inline=False)
    embed.add_field(name="🎭 Rol Sistemi", value="`/rolver` `/rolal` `/toplurol`", inline=False)
    embed.add_field(name="⚖️ Moderasyon", value="`/ban` `/kick` `/ipban` `/uyari` `/uyarilar`", inline=False)
    embed.add_field(name="📊 İstatistik", value="`/profil` `/liderlik` `/gunluk`", inline=False)
    embed.add_field(name="🎮 RP", value="`/karakter` `/basvuru`", inline=False)
    embed.add_field(name="🎉 Etkinlik", value="`/cekiliş` `/anket` `/duyuru`", inline=False)
    embed.add_field(name="⚙️ Yönetim", value="`/log_kanal` `/ticket_kategori` `/ayarlar`", inline=False)
    embed.set_footer(text="Sancak RP • Destek Sistemi")
    await interaction.response.send_message(embed=embed)

# ========================================
# KAYIT SİSTEMİ
# ========================================

class KayitFormu(discord.ui.Modal, title="Whitelist Başvuru Formu"):
    soru1 = discord.ui.TextInput(
        label="1. Adınız, Yaşınız ve Bizi Nereden Buldunuz?",
        style=discord.TextStyle.short,
        placeholder="Gerçek adınız, yaşınız ve sunucuyu bulma şekliniz.",
        required=True
    )
    soru2 = discord.ui.TextInput(
        label="2. Meta Gaming ve Fail RP Nedir?",
        style=discord.TextStyle.paragraph,
        placeholder="Lütfen iki terimi de kendi cümlelerinizle açıklayın.",
        required=True
    )
    soru3 = discord.ui.TextInput(
        label="3. IC ve OOC Nedir?",
        style=discord.TextStyle.paragraph,
        placeholder="IC (In Character) ve OOC (Out of Character) nedir?",
        required=True
    )
    soru4 = discord.ui.TextInput(
        label="4. VDM ve RDM Nedir?",
        style=discord.TextStyle.paragraph,
        placeholder="VDM ve RDM kurallarını kısaca açıklayın.",
        required=True
    )
    soru5 = discord.ui.TextInput(
        label="5. Örnek Kaza Rolü (/me ve /do)",
        style=discord.TextStyle.paragraph,
        placeholder="/me ve /do kullanarak örnek bir kaza rolü yazın.",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        log_kanal_id = ayar_al("kayit_log_kanal")
        if not log_kanal_id:
            await interaction.response.send_message("❌ Kayıt log kanalı ayarlanmamış!", ephemeral=True)
            return
        log_kanal = interaction.guild.get_channel(int(log_kanal_id))
        if not log_kanal:
            await interaction.response.send_message("❌ Log kanalı bulunamadı!", ephemeral=True)
            return

        embed = discord.Embed(
            title="📝 Yeni Whitelist Başvurusu",
            description=f"**Başvuran:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                        f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.blue()
        )
        embed.add_field(name="1. Ad, Yaş, Kaynak", value=self.soru1.value[:1024], inline=False)
        embed.add_field(name="2. Meta Gaming & Fail RP", value=self.soru2.value[:1024], inline=False)
        embed.add_field(name="3. IC & OOC", value=self.soru3.value[:1024], inline=False)
        embed.add_field(name="4. VDM & RDM", value=self.soru4.value[:1024], inline=False)
        embed.add_field(name="5. Örnek Kaza Rolü", value=self.soru5.value[:1024], inline=False)
        embed.set_footer(text="Sancak Roleplay • Whitelist Sistemi")

        view = KayitOnay(interaction.user.id)
        await log_kanal.send(embed=embed, view=view)

        await interaction.response.send_message(
            "✅ Başvurunuz alındı! Yetkililer en kısa sürede inceleyecek. Sonuç DM'den bildirilecek.",
            ephemeral=True
        )


class KayitOnay(discord.ui.View):
    def __init__(self, kullanici_id: int):
        super().__init__(timeout=None)
        self.kullanici_id = kullanici_id

    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Bu butonu kullanma yetkin yok!", ephemeral=True)
            return

        uye = interaction.guild.get_member(self.kullanici_id)
        if not uye:
            await interaction.response.send_message("❌ Kullanıcı sunucuda bulunamadı.", ephemeral=True)
            return

        rol_id = ayar_al("kayit_verilecek_rol")
        try:
            if rol_id:
                rol = interaction.guild.get_role(int(rol_id))
                if rol:
                    await uye.add_roles(rol)
            await uye.send("🎉 Tebrikler! Kaydınız kabul edildi. İyi rol yapmalar!")
        except:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message(f"✅ {uye.mention} onaylandı ve rol verildi.", ephemeral=True)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Bu butonu kullanma yetkin yok!", ephemeral=True)
            return

        uye = interaction.guild.get_member(self.kullanici_id)
        try:
            if uye:
                await uye.send("Üzgünüz, başvurunuz reddedildi. Tekrar deneyebilirsiniz.")
        except:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("❌ Başvuru reddedildi.", ephemeral=True)


class KayitPaneli(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, emoji="➕", custom_id="kayit_ol")
    async def kayit_ol(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KayitFormu())


@bot.tree.command(name="kayitkur", description="Kayıt panelini kurar")
@app_commands.default_permissions(administrator=True)
async def kayitkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 TURAN ROLEPLAY KAYIT SİSTEMİ",
        description="**Hoş Geldiniz!**\n\n"
                    "Sunucumuza katılmak ve rol yapmaya başlamak için öncelikle kayıt başvurusunda bulunmanız gerekmektedir.\n\n"
                    "Aşağıdaki buton aracılığıyla başvuru formunu doldurabilirsiniz. "
                    "Başvurunuz yetkili ekibimiz tarafından incelenecek ve en kısa sürede sonuçlandırılacaktır.\n\n"
                    "⚠️ **Unutmayın:** Lütfen formu doldururken kurallarımızı ve temel rol yapma terimlerini "
                    "(Meta Gaming, Fail RP vb.) bildiğinizden emin olun.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sancak Roleplay • Whitelist Sistemi")
    await interaction.channel.send(embed=embed, view=KayitPaneli())
    await interaction.response.send_message("✅ Kayıt paneli kuruldu.", ephemeral=True)


@bot.tree.command(name="kayit_ayar", description="Kayıt sistemini ayarlar (Admin)")
@app_commands.default_permissions(administrator=True)
async def kayit_ayar(interaction: discord.Interaction, log_kanal: discord.TextChannel, verilecek_rol: discord.Role):
    ayar_koy("kayit_log_kanal", log_kanal.id)
    ayar_koy("kayit_verilecek_rol", verilecek_rol.id)
    embed = discord.Embed(
        title="✅ Kayıt Sistemi Ayarlandı",
        description=f"**Log Kanalı:** {log_kanal.mention}\n**Verilecek Rol:** {verilecek_rol.mention}",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================================
# TICKET SİSTEMİ
# ========================================

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Oyun İçi Destek", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="ticket_oyun")
    async def oyun(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_ac(interaction, "Oyun İçi Destek")

    @discord.ui.button(label="Teknik Destek", style=discord.ButtonStyle.secondary, emoji="🔧", custom_id="ticket_teknik")
    async def teknik(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_ac(interaction, "Teknik Destek")

    @discord.ui.button(label="Donate", style=discord.ButtonStyle.success, emoji="🛒", custom_id="ticket_donate")
    async def donate(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_ac(interaction, "Donate")

    @discord.ui.button(label="AntiCheat", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="ticket_anticheat")
    async def anticheat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await ticket_ac(interaction, "AntiCheat")


async def ticket_ac(interaction: discord.Interaction, kategori: str):
    guild = interaction.guild
    user = interaction.user
    
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT kanal_id FROM tickets WHERE kullanici_id = ? AND durum = 'acik'", (user.id,))
    kayit = c.fetchone()
    if kayit:
        kanal = guild.get_channel(kayit[0])
        if kanal:
            await interaction.response.send_message(f"❌ Zaten açık ticketın var: {kanal.mention}", ephemeral=True)
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
                    f"**Kategori:** {kategori}\n"
                    f"**Oluşturan:** {user.mention}\n"
                    f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        color=discord.Color.blue()
    )
    await kanal.send(content=user.mention, embed=embed, view=TicketKontrol())
    await interaction.response.send_message(f"✅ Ticket açıldı: {kanal.mention}", ephemeral=True)


class TicketKontrol(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Çözüldü", style=discord.ButtonStyle.success, emoji="✅", custom_id="ticket_cozuldu")
    async def cozuldu(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = db_baglan()
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Çözüldü. Siliniyor...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_kapat")
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
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
async def ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Sancak RP Destek Sistemi",
        description="Bilet oluşturmak için butonlara tıklayın.",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TicketPanel())
    await interaction.response.send_message("✅ Panel kuruldu.", ephemeral=True)

# ========================================
# ROL SİSTEMİ
# ========================================

@bot.tree.command(name="rolver", description="Rol verir (Guard/Cmds)")
async def rolver(interaction: discord.Interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await kullanici.add_roles(rol)
        await interaction.response.send_message(embed=embed_yap("🎭 ROL VERİLDİ", f"{kullanici.mention} → {rol.mention}", discord.Color.green()))
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="rolal", description="Rol alır (Guard/Cmds)")
async def rolal(interaction: discord.Interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await kullanici.remove_roles(rol)
        await interaction.response.send_message(embed=embed_yap("🎭 ROL ALINDI", f"{kullanici.mention} ← {rol.mention}", discord.Color.red()))
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="toplurol", description="Tüm üyelere rol verir (Guard/Cmds)")
async def toplurol(interaction: discord.Interaction, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await interaction.response.send_message(f"🎭 {rol.mention} veriliyor...", ephemeral=True)
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
    await interaction.channel.send(f"✅ {sayac} üyeye verildi.")

# ========================================
# MODERASYON
# ========================================

@bot.tree.command(name="ban", description="Ban atar")
async def ban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await interaction.guild.ban(kullanici, reason=f"{sebep} | {interaction.user}")
        await interaction.response.send_message(embed=embed_yap("🔨 BAN", f"{kullanici.mention} banlandı.\n**Sebep:** {sebep}", discord.Color.dark_red()))
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="kick", description="Kick atar")
async def kick(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await kullanici.kick(reason=f"{sebep} | {interaction.user}")
        await interaction.response.send_message(embed=embed_yap("👢 KICK", f"{kullanici.mention} atıldı.\n**Sebep:** {sebep}", discord.Color.orange()))
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="ipban", description="IP ban atar")
async def ipban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await interaction.guild.ban(kullanici, reason=f"[IP BAN] {sebep} | {interaction.user}")
        conn = db_baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ipbanlar (user_id, sebep, tarih, yetkili_id) VALUES (?, ?, ?, ?)",
                  (kullanici.id, sebep, datetime.now().isoformat(), interaction.user.id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(embed=embed_yap("🚫 IP BAN", f"{kullanici.mention} IP banlandı.\n**Sebep:** {sebep}", discord.Color.dark_red()))
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="uyari", description="Uyarı verir")
async def uyari(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT INTO uyarilar (user_id, sebep, yetkili_id, tarih) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, interaction.user.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=embed_yap("⚠️ UYARI", f"{kullanici.mention} uyarıldı.\n**Sebep:** {sebep}", discord.Color.yellow()))


@bot.tree.command(name="uyarilar", description="Uyarıları gösterir")
async def uyarilar(interaction: discord.Interaction, kullanici: discord.Member):
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
# İSTATİSTİK
# ========================================

@bot.tree.command(name="profil", description="Profilini gösterir")
async def profil(interaction: discord.Interaction, kullanici: discord.Member = None):
    if kullanici is None:
        kullanici = interaction.user
    conn = db_baglan()
    c = conn.cursor()
    c.execute("SELECT mesaj, xp, seviye, uyari FROM uyeler WHERE user_id = ?", (kullanici.id,))
    kayit = c.fetchone()
    conn.close()
    m, xp, sv, uy = kayit if kayit else (0, 0, 1, 0)
    embed = discord.Embed(title=f"👤 {kullanici.display_name}", color=discord.Color.blue())
    if kullanici.avatar:
        embed.set_thumbnail(url=kullanici.avatar.url)
    embed.add_field(name="📊 Mesaj", value=m)
    embed.add_field(name="⭐ Seviye", value=sv)
    embed.add_field(name="✨ XP", value=xp)
    embed.add_field(name="⚠️ Uyarı", value=uy)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="liderlik", description="En aktifler")
async def liderlik(interaction: discord.Interaction):
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
    await interaction.response.send_message(embed=embed_yap("🏆 Liderlik", mesaj, discord.Color.gold()))


@bot.tree.command(name="gunluk", description="Günlük ödül alır")
async def gunluk(interaction: discord.Interaction):
    conn = db_baglan()
    c = conn.cursor()
    bugun = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT son_gunluk FROM uyeler WHERE user_id = ?", (interaction.user.id,))
    kayit = c.fetchone()
    if kayit and kayit[0] == bugun:
        await interaction.response.send_message("⏳ Bugünkü ödülünü zaten aldın!", ephemeral=True)
        conn.close()
        return
    odul = random.randint(50, 200)
    c.execute("INSERT INTO uyeler (user_id, xp, son_gunluk) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET xp = xp + ?, son_gunluk = ?",
              (interaction.user.id, odul, bugun, odul, bugun))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=embed_yap("🎁 GÜNLÜK ÖDÜL", f"**+{odul} XP** kazandın!", discord.Color.green()))

# ========================================
# RP SİSTEMİ
# ========================================

@bot.tree.command(name="karakter", description="Karakter kaydı oluşturur")
async def karakter(interaction: discord.Interaction, isim: str, yas: int, meslek: str, hikaye: str):
    conn = db_baglan()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO karakterler (user_id, isim, yas, meslek, hikaye) VALUES (?, ?, ?, ?, ?)",
              (interaction.user.id, isim, yas, meslek, hikaye))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="✅ Karakter Kaydedildi", color=discord.Color.green())
    embed.add_field(name="İsim", value=isim)
    embed.add_field(name="Yaş", value=yas)
    embed.add_field(name="Meslek", value=meslek)
    embed.add_field(name="Hikaye", value=hikaye[:1024], inline=False)
    await interaction.response.send_message(embed=embed)

# ========================================
# ETKİNLİK
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


@bot.tree.command(name="cekiliş", description="Çekiliş (Admin)")
@app_commands.default_permissions(administrator=True)
async def cekilis(interaction: discord.Interaction, odul: str, sure: int):
    embed = discord.Embed(
        title="🎉 ÇEKİLİŞ!",
        description=f"**Ödül:** {odul}\n**Süre:** {sure} saniye\n🎉 emojisine tıkla!",
        color=discord.Color.gold()
    )
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
# YÖNETİM
# ========================================

@bot.tree.command(name="log_kanal", description="Log kanalı (Admin)")
@app_commands.default_permissions(administrator=True)
async def log_kanal(interaction: discord.Interaction, kanal: discord.TextChannel):
    ayar_koy("log_kanal", kanal.id)
    await interaction.response.send_message(f"✅ Log kanalı {kanal.mention} olarak ayarlandı.", ephemeral=True)


@bot.tree.command(name="ticket_kategori", description="Ticket kategori (Admin)")
@app_commands.default_permissions(administrator=True)
async def ticket_kategori(interaction: discord.Interaction, kategori: discord.CategoryChannel):
    ayar_koy("ticket_kategori", kategori.id)
    await interaction.response.send_message(f"✅ Ticket kategorisi {kategori.name} olarak ayarlandı.", ephemeral=True)


@bot.tree.command(name="ayarlar", description="Bot ayarlarını gösterir")
async def ayarlar(interaction: discord.Interaction):
    log_k = ayar_al("log_kanal", "Ayarlanmadı")
    ticket_k = ayar_al("ticket_kategori", "Ayarlanmadı")
    kayit_log = ayar_al("kayit_log_kanal", "Ayarlanmadı")
    kayit_rol = ayar_al("kayit_verilecek_rol", "Ayarlanmadı")
    embed = discord.Embed(title="⚙️ Bot Ayarları", color=discord.Color.blue())
    embed.add_field(name="Log Kanalı", value=f"<#{log_k}>" if log_k != "Ayarlanmadı" else log_k)
    embed.add_field(name="Ticket Kategorisi", value=f"<#{ticket_k}>" if ticket_k != "Ayarlanmadı" else ticket_k)
    embed.add_field(name="Kayıt Log Kanalı", value=f"<#{kayit_log}>" if kayit_log != "Ayarlanmadı" else kayit_log)
    embed.add_field(name="Kayıt Verilecek Rol", value=f"<@&{kayit_rol}>" if kayit_rol != "Ayarlanmadı" else kayit_rol)
    await interaction.response.send_message(embed=embed)

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
