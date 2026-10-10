import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import io
import json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from database import kur, baglan, log_ekle, ayar_al, ayar_koy

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

kur()

# ========================================
# YETKİLİ ROLLER
# ========================================

YETKILI_ROLLER = ["Guard", "/Cmds", "Vise Team"]
MOD_ROLLER = ["Guard", "/Cmds"]
TICKET_ROLLER = ["Vise Team", "Guard"]

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
    
    conn = baglan()
    c = conn.cursor()
    c.execute("INSERT INTO uyeler (user_id, mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET mesaj = mesaj + 1", (message.author.id,))
    c.execute("SELECT mesaj, xp, seviye FROM uyeler WHERE user_id = ?", (message.author.id,))
    kayit = c.fetchone()
    if kayit:
        mesaj_s, xp, seviye = kayit
        yeni_xp = xp + random.randint(5, 15)
        yeni_seviye = mesaj_s // 50 + 1
        c.execute("UPDATE uyeler SET xp = ?, seviye = ? WHERE user_id = ?", (yeni_xp, yeni_seviye, message.author.id))
        
        # Seviye atladıysa
        if yeni_seviye > seviye:
            try:
                await message.channel.send(f"🎉 {message.author.mention} **{yeni_seviye}. seviyeye** ulaştı!")
            except:
                pass
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
        description="Kullanılabilir komutlar:",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="🎫 Ticket", value="`/ticketkur` `/ticketkapat`", inline=False)
    embed.add_field(name="🎭 Rol Sistemi", value="`/rolver` `/rolal` `/toplurol` `/rolmenu`", inline=False)
    embed.add_field(name="⚖️ Moderasyon", value="`/ban` `/kick` `/ipban` `/uyari` `/uyarilar`", inline=False)
    embed.add_field(name="📊 İstatistik", value="`/profil` `/seviye` `/liderlik` `/gunluk`", inline=False)
    embed.add_field(name="🎮 RP", value="`/karakter` `/basvuru`", inline=False)
    embed.add_field(name="🎉 Etkinlik", value="`/cekiliş` `/anket` `/duyuru`", inline=False)
    embed.add_field(name="⚙️ Yönetim", value="`/log_kanal` `/ayarlar` `/hoşgeldin`", inline=False)
    embed.set_footer(text="Sancak RP • Destek Sistemi", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await interaction.response.send_message(embed=embed)

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
    
    conn = baglan()
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
                    f"**Destek ID:** #{ticket_sayisi:04d}\n"
                    f"**Kategori:** {kategori}\n"
                    f"**Oluşturan:** {user.mention}\n"
                    f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sancak RP Destek Sistemi")
    await kanal.send(content=user.mention + " | Yetkililer ilgilenecek.", embed=embed, view=TicketKontrol())
    await interaction.response.send_message(f"✅ Ticket açıldı: {kanal.mention}", ephemeral=True)
    await log_gonder(guild, "TICKET", user, f"{kategori} - {kanal.mention}")


class TicketKontrol(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Claim", style=discord.ButtonStyle.secondary, emoji="🙋", custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"✅ {interaction.user.mention} ticketı üstlendi.")

    @discord.ui.button(label="Beklemede", style=discord.ButtonStyle.primary, emoji="⏸️", custom_id="ticket_bekleme")
    async def bekleme(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏸️ Ticket beklemede.")

    @discord.ui.button(label="İnceleniyor", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="ticket_inceleniyor")
    async def inceleniyor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔍 İnceleniyor.")

    @discord.ui.button(label="Çözüldü", style=discord.ButtonStyle.success, emoji="✅", custom_id="ticket_cozuldu")
    async def cozuldu(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = baglan()
        c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (interaction.channel.id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ Çözüldü. 5 saniye içinde siliniyor...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_kapat")
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = baglan()
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
        description="Bilet oluşturmadan önce aşağıdaki kuralları okuyunuz. Aşağıdaki butonlardan size uygun kategoriyi seçerek destek talebi oluşturabilirsiniz.\n\n"
                    "**Genel Kurallar:**\n"
                    "• Biletinizi 24 saat içinde kontrol etmek zorundasınız.\n"
                    "• Yönetim üyelerine özel mesaj atmaktan kaçının.\n"
                    "• Sorunlarınızı bilet aracılığıyla iletin.\n\n"
                    "**Sorun Bildirimi:**\n"
                    "• Sorunu detaylı açıklayın.\n"
                    "• Gerekli bilgileri eksiksiz paylaşın.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sancak RP • Destek")
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
        await log_gonder(interaction.guild, "ROL VERME", interaction.user, f"{kullanici} → {rol.name}")
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
        await log_gonder(interaction.guild, "ROL ALMA", interaction.user, f"{kullanici} → {rol.name}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="toplurol", description="Tüm üyelere rol verir (Guard/Cmds)")
async def toplurol(interaction: discord.Interaction, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    await interaction.response.send_message(f"🎭 {rol.mention} tüm üyelere veriliyor...", ephemeral=True)
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
    await interaction.channel.send(f"✅ {sayac} üyeye {rol.mention} verildi.")

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
        await log_gonder(interaction.guild, "BAN", interaction.user, f"{kullanici} - {sebep}")
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
        await log_gonder(interaction.guild, "KICK", interaction.user, f"{kullanici} - {sebep}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="ipban", description="IP ban atar (Guard/Cmds)")
async def ipban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    try:
        await interaction.guild.ban(kullanici, reason=f"[IP BAN] {sebep} | {interaction.user}")
        conn = baglan()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ipbanlar (user_id, sebep, tarih, yetkili_id) VALUES (?, ?, ?, ?)",
                  (kullanici.id, sebep, datetime.now().isoformat(), interaction.user.id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(embed=embed_yap("🚫 IP BAN", f"{kullanici.mention} IP banlandı.\n**Sebep:** {sebep}", discord.Color.dark_red()))
        await log_gonder(interaction.guild, "IP BAN", interaction.user, f"{kullanici} - {sebep}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)


@bot.tree.command(name="uyari", description="Uyarı verir")
async def uyari(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True)
        return
    conn = baglan()
    c = conn.cursor()
    c.execute("INSERT INTO uyarilar (user_id, sebep, yetkili_id, tarih) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, interaction.user.id, datetime.now().isoformat()))
    c.execute("UPDATE uyeler SET uyari = uyari + 1 WHERE user_id = ?", (kullanici.id,))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=embed_yap("⚠️ UYARI", f"{kullanici.mention} uyarıldı.\n**Sebep:** {sebep}", discord.Color.yellow()))


@bot.tree.command(name="uyarilar", description="Uyarıları gösterir")
async def uyarilar(interaction: discord.Interaction, kullanici: discord.Member):
    conn = baglan()
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
    conn = baglan()
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
    embed.add_field(name="📅 Katılma", value=kullanici.joined_at.strftime('%d/%m/%Y'))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="liderlik", description="En aktifler")
async def liderlik(interaction: discord.Interaction):
    conn = baglan()
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
    conn = baglan()
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
    conn = baglan()
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


@bot.tree.command(name="basvuru", description="Başvuru yapar")
async def basvuru(interaction: discord.Interaction, tip: str, icerik: str):
    conn = baglan()
    c = conn.cursor()
    c.execute("INSERT INTO basvurular (user_id, tip, icerik, durum, tarih) VALUES (?, ?, ?, 'beklemede', ?)",
              (interaction.user.id, tip, icerik, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await interaction.response.send_message(embed=embed_yap("📝 BAŞVURU ALINDI", f"**Tip:** {tip}\n**Durum:** Beklemede", discord.Color.blue()))
    await log_gonder(interaction.guild, "BAŞVURU", interaction.user, f"{tip}: {icerik[:100]}")

# ========================================
# ETKİNLİK
# ========================================

@bot.tree.command(name="duyuru", description="Duyuru atar (Admin)")
@app_commands.default_permissions(administrator=True)
async def duyuru(interaction: discord.Interaction, baslik: str, mesaj: str):
    embed = discord.Embed(title=f"📢 {baslik}", description=mesaj, color=discord.Color.red(), timestamp=datetime.now())
    embed.set_footer(text=f"Duyuran: {interaction.user.display_name}")
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

@bot.tree.command(name="log_kanal", description="Log kanalını ayarlar (Admin)")
@app_commands.default_permissions(administrator=True)
async def log_kanal(interaction: discord.Interaction, kanal: discord.TextChannel):
    ayar_koy("log_kanal", kanal.id)
    await interaction.response.send_message(f"✅ Log kanalı {kanal.mention} olarak ayarlandı.", ephemeral=True)


@bot.tree.command(name="ticket_kategori", description="Ticket kategori ayarlar (Admin)")
@app_commands.default_permissions(administrator=True)
async def ticket_kategori(interaction: discord.Interaction, kategori: discord.CategoryChannel):
    ayar_koy("ticket_kategori", kategori.id)
    await interaction.response.send_message(f"✅ Ticket kategorisi {kategori.name} olarak ayarlandı.", ephemeral=True)


@bot.tree.command(name="ayarlar", description="Bot ayarlarını gösterir")
async def ayarlar(interaction: discord.Interaction):
    log_k = ayar_al("log_kanal", "Ayarlanmadı")
    ticket_k = ayar_al("ticket_kategori", "Ayarlanmadı")
    embed = discord.Embed(title="⚙️ Bot Ayarları", color=discord.Color.blue())
    embed.add_field(name="Log Kanalı", value=f"<#{log_k}>" if log_k != "Ayarlanmadı" else log_k)
    embed.add_field(name="Ticket Kategorisi", value=f"<#{ticket_k}>" if ticket_k != "Ayarlanmadı" else ticket_k)
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
