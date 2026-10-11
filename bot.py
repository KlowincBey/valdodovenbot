import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import random
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask
from threading import Thread

# ========================================
# FLASK
# ========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Sancak RP Botu Aktif! 🛡️"

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
# GÜVENLİK AYARLARI
# ========================================
GUARD_AKTIF = True
ANTI_RAID_AKTIF = True
ANTI_SPAM_AKTIF = True
ANTI_LINK_AKTIF = True
ANTI_KUFUR_AKTIF = True
BOT_KORUMA_AKTIF = True
YENI_HESAP_GUN = 7

LIMIT_CHANNEL_DELETE = 3
LIMIT_CHANNEL_CREATE = 5
LIMIT_ROLE_DELETE = 3
LIMIT_ROLE_CREATE = 5
LIMIT_BAN = 3
LIMIT_KICK = 3
LIMIT_TIME = 10

SPAM_MESAJ_LIMIT = 5
SPAM_MENTION_LIMIT = 5
SPAM_SURE = 5

YASAKLI_KELIMELER = ["aptal", "salak", "gerizekalı", "amk", "sg", "siktir", "orospu", "pezevenk", "yarrak", "amcık"]

# Bot koruma
IZINLI_BOTLAR = []
BOT_CEZA_TURU = "ban"
BOT_EKLEYEN_CEZA = "ban"

user_actions = defaultdict(list)
user_messages = defaultdict(list)

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
    if member.id == member.guild.owner_id:
        return True
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
# GÜVENLİK FONKSİYONLARI
# ========================================
def action_kaydet(user_id, aksiyon):
    simdi = datetime.now().timestamp()
    user_actions[user_id] = [(a, t) for a, t in user_actions[user_id] if simdi - t < LIMIT_TIME]
    user_actions[user_id].append((aksiyon, simdi))
    ayni = [a for a, t in user_actions[user_id] if a == aksiyon]
    return len(ayni)

async def guvenlik_log(guild, tip, kullanici, aciklama):
    log_id = ayar_al("guvenlik_log_kanal")
    if not log_id:
        return
    log = guild.get_channel(int(log_id))
    if not log:
        return
    try:
        embed = discord.Embed(
            title=f"🛡️ {tip}",
            description=f"**Kullanıcı:** {kullanici.mention if hasattr(kullanici, 'mention') else kullanici}\n"
                        f"**Açıklama:** {aciklama}\n"
                        f"**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Sancak Roleplay • Güvenlik Sistemi")
        await log.send(embed=embed)
    except:
        pass

async def cezalandir(guild, uye, sebep, ceza="rol_al"):
    if uye.id == guild.owner_id:
        return
    if uye.id == bot.user.id:
        return
    if guild.me.top_role <= uye.top_role:
        await guvenlik_log(guild, "⚠️ CEZA VERİLEMEDİ", uye,
                           f"Botun rolü düşük! Sebep: {sebep}")
        return
    try:
        if ceza == "ban":
            await guild.ban(uye, reason=f"[GÜVENLİK] {sebep}")
            await guvenlik_log(guild, "🔨 BAN ATILDI", uye, sebep)
        elif ceza == "kick":
            await uye.kick(reason=f"[GÜVENLİK] {sebep}")
            await guvenlik_log(guild, "👢 KICK ATILDI", uye, sebep)
        elif ceza == "rol_al":
            for rol in uye.roles:
                if rol.permissions.administrator or rol.permissions.manage_guild or rol.permissions.manage_roles or rol.permissions.manage_channels:
                    try:
                        await uye.remove_roles(rol, reason=f"[GÜVENLİK] {sebep}")
                    except:
                        pass
            await guvenlik_log(guild, "🛡️ ROL ALINDI", uye, sebep)
    except Exception as e:
        await guvenlik_log(guild, "❌ CEZA HATA", uye, f"{sebep} - {e}")

def yeni_hesap_mi(uye):
    if not uye.created_at:
        return False
    fark = datetime.now(uye.created_at.tzinfo) - uye.created_at
    return fark.days < YENI_HESAP_GUN

# ========================================
# HAZIR
# ========================================
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/yardim | Sancak RP 🛡️"))
    print(f'✅ Sancak RP Güvenlik Tanrısı hazır: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash komut senkronize edildi.")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")

# ========================================
# GÜVENLİK EVENTLERİ
# ========================================
@bot.event
async def on_guild_channel_delete(channel):
    if not GUARD_AKTIF: return
    guild = channel.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                uye = entry.user
                if uye.id == bot.user.id or uye.id == guild.owner_id: return
                if yetkili_mi(uye, YETKILI_ROLLER): return
                if action_kaydet(uye.id, "channel_delete") >= LIMIT_CHANNEL_DELETE:
                    await cezalandir(guild, uye, f"{LIMIT_TIME}s içinde kanal sildi (ANTI-NUKE)", "ban")
                break
    except: pass

@bot.event
async def on_guild_channel_create(channel):
    if not GUARD_AKTIF: return
    guild = channel.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                uye = entry.user
                if uye.id == bot.user.id or uye.id == guild.owner_id: return
                if yetkili_mi(uye, YETKILI_ROLLER): return
                if action_kaydet(uye.id, "channel_create") >= LIMIT_CHANNEL_CREATE:
                    try: await channel.delete(reason="ANTI-NUKE")
                    except: pass
                    await cezalandir(guild, uye, f"Kanal spam (ANTI-NUKE)", "ban")
                break
    except: pass

@bot.event
async def on_guild_role_delete(role):
    if not GUARD_AKTIF: return
    guild = role.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                uye = entry.user
                if uye.id == bot.user.id or uye.id == guild.owner_id: return
                if yetkili_mi(uye, YETKILI_ROLLER): return
                if action_kaydet(uye.id, "role_delete") >= LIMIT_ROLE_DELETE:
                    await cezalandir(guild, uye, f"Rol silme spam (ANTI-NUKE)", "ban")
                break
    except: pass

@bot.event
async def on_guild_role_create(role):
    if not GUARD_AKTIF: return
    guild = role.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            if entry.target.id == role.id:
                uye = entry.user
                if uye.id == bot.user.id or uye.id == guild.owner_id: return
                if yetkili_mi(uye, YETKILI_ROLLER): return
                if action_kaydet(uye.id, "role_create") >= LIMIT_ROLE_CREATE:
                    try: await role.delete(reason="ANTI-NUKE")
                    except: pass
                    await cezalandir(guild, uye, f"Rol spam (ANTI-NUKE)", "ban")
                break
    except: pass

@bot.event
async def on_member_ban(guild, user):
    if not GUARD_AKTIF: return
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                uye = entry.user
                if uye.id == bot.user.id or uye.id == guild.owner_id: return
                if yetkili_mi(uye, YETKILI_ROLLER): return
                if action_kaydet(uye.id, "ban") >= LIMIT_BAN:
                    try: await guild.unban(user, reason="ANTI-NUKE")
                    except: pass
                    await cezalandir(guild, uye, f"Toplu ban (ANTI-NUKE)", "ban")
                break
    except: pass

@bot.event
async def on_member_remove(member):
    if not GUARD_AKTIF: return
    guild = member.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                uye = entry.user
                if uye.id == bot.user.id or uye.id == guild.owner_id: return
                if yetkili_mi(uye, YETKILI_ROLLER): return
                if action_kaydet(uye.id, "kick") >= LIMIT_KICK:
                    await cezalandir(guild, uye, f"Toplu kick (ANTI-NUKE)", "ban")
                break
    except: pass

@bot.event
async def on_webhooks_update(channel):
    if not GUARD_AKTIF: return
    guild = channel.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
            uye = entry.user
            if uye.id == bot.user.id or uye.id == guild.owner_id: return
            if yetkili_mi(uye, YETKILI_ROLLER): return
            await cezalandir(guild, uye, "İzinsiz webhook oluşturdu", "rol_al")
            try:
                webhooks = await channel.webhooks()
                for wh in webhooks:
                    if wh.user and wh.user.id == uye.id:
                        await wh.delete(reason="ANTI-NUKE")
            except: pass
            break
    except: pass

# ========================================
# ÜYE KATILMA (BOT KORUMA + ANTI-RAID + DM)
# ========================================
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    # BOT KORUMASI
    if member.bot:
        if not BOT_KORUMA_AKTIF:
            return
        if member.id in IZINLI_BOTLAR or member.id == bot.user.id:
            return
        
        ekleyen = None
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    ekleyen = entry.user
                    break
        except: pass
        
        try:
            if BOT_CEZA_TURU == "ban":
                await guild.ban(member, reason="🚫 İZİNSİZ BOT")
            elif BOT_CEZA_TURU == "kick":
                await member.kick(reason="🚫 İZİNSİZ BOT")
        except: pass
        
        if ekleyen and ekleyen.id != guild.owner_id and ekleyen.id != bot.user.id:
            await cezalandir(guild, ekleyen, f"İzinsiz bot ekledi: {member.name}", BOT_EKLEYEN_CEZA)
        
        await guvenlik_log(guild, "🚫 İZİNSİZ BOT ENGELLENDİ",
                          ekleyen if ekleyen else "Bilinmiyor",
                          f"Bot: **{member.name}** (`{member.id}`)\nEkleyen: {ekleyen.mention if ekleyen else '?'}")
        
        try:
            dm = discord.Embed(title="🚨 ACİL: İZİNSİZ BOT!",
                description=f"**Sunucu:** {guild.name}\n**Bot:** {member.name}\n**Ekleyen:** {ekleyen.mention if ekleyen else '?'}\n✅ Koruma devrede!",
                color=discord.Color.red(), timestamp=datetime.now())
            await guild.owner.send(embed=dm)
        except: pass
        return
    
    # ANTI-RAID
    if ANTI_RAID_AKTIF and yeni_hesap_mi(member):
        try:
            await member.send(f"❌ **{guild.name}** sunucusuna katılamazsın. Hesabın çok yeni.")
        except: pass
        try: await member.kick(reason="ANTI-RAID: Yeni hesap")
        except: pass
        await guvenlik_log(guild, "🚫 ANTI-RAID", member, "Yeni hesap")
        return
    
    # Hoş geldin DM
    try:
        embed = discord.Embed(
            title="👋 Sancak Roleplay'e Hoş Geldin!",
            description=f"Merhaba **{member.display_name}**,\n\n"
                        f"**{guild.name}** sunucumuza hoş geldin!\n\n"
                        f"Rol yapmaya başlamadan önce kayıt olman gerekiyor.\n\n"
                        f"📝 Kayıt olmak için sunucudaki **kayıt kanalına** git, "
                        f"**Kayıt Ol** butonuna tıkla ve formu doldur.",
            color=discord.Color.blue())
        embed.set_footer(text="Sancak Roleplay • Kayıt Sistemi")
        await member.send(embed=embed)
    except: pass

# ========================================
# MESAJ (XP + KORUMA)
# ========================================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    uye = message.author
    guild = message.guild
    
    # SPAM
    if ANTI_SPAM_AKTIF and not yetkili_mi(uye, YETKILI_ROLLER):
        simdi = datetime.now().timestamp()
        user_messages[uye.id] = [t for t in user_messages[uye.id] if simdi - t < SPAM_SURE]
        user_messages[uye.id].append(simdi)
        
        if len(user_messages[uye.id]) > SPAM_MESAJ_LIMIT:
            try: await message.delete()
            except: pass
            try:
                await uye.timeout(timedelta(minutes=5), reason="Spam")
                await message.channel.send(f"⏸️ {uye.mention} spam yaptı, 5 dk susturuldu.", delete_after=5)
            except: pass
            await guvenlik_log(guild, "⚠️ SPAM", uye, "Mesaj spam")
            user_messages[uye.id] = []
            return
        
        if len(message.mentions) > SPAM_MENTION_LIMIT:
            try: await message.delete()
            except: pass
            try:
                await uye.timeout(timedelta(minutes=5), reason="Mention spam")
                await message.channel.send(f"⏸️ {uye.mention} mention spam, 5 dk susturuldu.", delete_after=5)
            except: pass
            await guvenlik_log(guild, "⚠️ MENTION SPAM", uye, f"{len(message.mentions)} mention")
            return
    
    # KÜFÜR
    if ANTI_KUFUR_AKTIF and not yetkili_mi(uye, YETKILI_ROLLER):
        for kelime in YASAKLI_KELIMELER:
            if kelime in message.content.lower():
                try:
                    await message.delete()
                    await message.channel.send(f"⚠️ {uye.mention} küfür yasak!", delete_after=5)
                except: pass
                await guvenlik_log(guild, "⚠️ KÜFÜR", uye, message.content[:100])
                return
    
    # LİNK
    if ANTI_LINK_AKTIF and not yetkili_mi(uye, YETKILI_ROLLER):
        icerik = message.content.lower()
        if "discord.gg/" in icerik or "http://" in icerik or "https://" in icerik:
            try:
                await message.delete()
                await message.channel.send(f"🚫 {uye.mention} link yasak!", delete_after=5)
            except: pass
            await guvenlik_log(guild, "⚠️ LİNK", uye, message.content[:100])
            return
    
    # XP
    conn = db_baglan(); c = conn.cursor()
    c.execute("INSERT INTO uyeler (user_id, mesaj) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET mesaj = mesaj + 1", (uye.id,))
    c.execute("SELECT mesaj, xp, seviye FROM uyeler WHERE user_id = ?", (uye.id,))
    kayit = c.fetchone()
    if kayit:
        ms, xp, sv = kayit
        yxp = xp + random.randint(5, 15)
        ysv = ms // 50 + 1
        c.execute("UPDATE uyeler SET xp = ?, seviye = ? WHERE user_id = ?", (yxp, ysv, uye.id))
        if ysv > sv:
            try: await message.channel.send(f"🎉 {uye.mention} **{ysv}. seviyeye** ulaştı!")
            except: pass
    conn.commit(); conn.close()
    await bot.process_commands(message)

# ========================================
# GÜVENLİK KOMUTLARI
# ========================================
@bot.tree.command(name="guard", description="Guard (Anti-Nuke) açar/kapatır")
@app_commands.describe(durum="on veya off")
@app_commands.default_permissions(administrator=True)
async def guard_cmd(interaction, durum: str):
    global GUARD_AKTIF
    if durum.lower() == "on":
        GUARD_AKTIF = True
        await interaction.response.send_message("🛡️ **Guard AKTİF!**", ephemeral=True)
    elif durum.lower() == "off":
        GUARD_AKTIF = False
        await interaction.response.send_message("⚠️ **Guard PASİF!**", ephemeral=True)
    else:
        await interaction.response.send_message("❌ `/guard on` veya `/guard off`", ephemeral=True)

@bot.tree.command(name="guvenlik_log", description="Güvenlik log kanalını ayarlar")
@app_commands.default_permissions(administrator=True)
async def guvenlik_log_cmd(interaction, kanal: discord.TextChannel):
    ayar_koy("guvenlik_log_kanal", kanal.id)
    await interaction.response.send_message(f"✅ Güvenlik log: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="idban", description="ID ile ban atar")
async def idban(interaction, kullanici_id: str, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    try:
        uid = int(kullanici_id)
    except:
        await interaction.response.send_message("❌ Geçersiz ID!", ephemeral=True); return
    try:
        user = await bot.fetch_user(uid)
        await interaction.guild.ban(user, reason=f"{sebep} | {interaction.user}")
        embed = discord.Embed(title="🔨 ID BAN",
            description=f"**Kullanıcı:** {user.mention} (`{user.id}`)\n**Sebep:** {sebep}\n**Yetkili:** {interaction.user.mention}",
            color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed)
        await guvenlik_log(interaction.guild, "🔨 ID BAN", interaction.user, f"{user.name} - {sebep}")
    except discord.NotFound:
        await interaction.response.send_message(f"❌ `{kullanici_id}` bulunamadı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="lockdown", description="Sunucuyu kilitler")
@app_commands.default_permissions(administrator=True)
async def lockdown(interaction):
    await interaction.response.send_message("🔒 **LOCKDOWN!**", ephemeral=True)
    sayac = 0
    for ch in interaction.guild.text_channels:
        try:
            ow = ch.overwrites_for(interaction.guild.default_role)
            ow.send_messages = False
            await ch.set_permissions(interaction.guild.default_role, overwrite=ow)
            sayac += 1
        except: pass
    await guvenlik_log(interaction.guild, "🔒 LOCKDOWN", interaction.user, f"{sayac} kanal kilitlendi")

@bot.tree.command(name="unlock", description="Kilidi açar")
@app_commands.default_permissions(administrator=True)
async def unlock(interaction):
    await interaction.response.send_message("🔓 **Açılıyor...**", ephemeral=True)
    sayac = 0
    for ch in interaction.guild.text_channels:
        try:
            ow = ch.overwrites_for(interaction.guild.default_role)
            ow.send_messages = None
            await ch.set_permissions(interaction.guild.default_role, overwrite=ow)
            sayac += 1
        except: pass
    await guvenlik_log(interaction.guild, "🔓 UNLOCK", interaction.user, f"{sayac} kanal açıldı")

@bot.tree.command(name="guvenlik_durum", description="Güvenlik durumunu gösterir")
async def guvenlik_durum(interaction):
    embed = discord.Embed(title="🛡️ Sancak RP Güvenlik Durumu", color=discord.Color.green())
    embed.add_field(name="🛡️ Anti-Nuke", value="✅" if GUARD_AKTIF else "❌", inline=True)
    embed.add_field(name="🚫 Anti-Raid", value="✅" if ANTI_RAID_AKTIF else "❌", inline=True)
    embed.add_field(name="⚠️ Anti-Spam", value="✅" if ANTI_SPAM_AKTIF else "❌", inline=True)
    embed.add_field(name="🔗 Anti-Link", value="✅" if ANTI_LINK_AKTIF else "❌", inline=True)
    embed.add_field(name="🤬 Anti-Küfür", value="✅" if ANTI_KUFUR_AKTIF else "❌", inline=True)
    embed.add_field(name="🤖 Bot Koruma", value="✅" if BOT_KORUMA_AKTIF else "❌", inline=True)
    embed.add_field(name="🆕 Hesap Sınırı", value=f"{YENI_HESAP_GUN} gün", inline=True)
    embed.add_field(name="📊 Ban Limit", value=f"{LIMIT_BAN}/{LIMIT_TIME}s", inline=True)
    embed.add_field(name="🤖 Bot Ceza", value=BOT_CEZA_TURU.upper(), inline=True)
    embed.set_footer(text="Sancak Roleplay • Güvenlik Tanrısı")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bot_ayar", description="Bot koruma ayarları")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(bot_id="İzin verilecek bot ID", ceza="ban/kick")
async def bot_ayar(interaction, bot_id: str = None, ceza: str = None):
    global BOT_CEZA_TURU
    if bot_id:
        try:
            bid = int(bot_id)
            if bid not in IZINLI_BOTLAR:
                IZINLI_BOTLAR.append(bid)
                await interaction.response.send_message(f"✅ Bot `{bid}` izinli listeye eklendi.", ephemeral=True)
            else:
                await interaction.response.send_message(f"⚠️ Zaten izinli.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Geçersiz ID!", ephemeral=True); return
    if ceza:
        if ceza.lower() in ["ban", "kick"]:
            BOT_CEZA_TURU = ceza.lower()
            await interaction.response.send_message(f"✅ Bot ceza: **{ceza.upper()}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Sadece ban/kick.", ephemeral=True)
    if not bot_id and not ceza:
        await interaction.response.send_message(
            f"**Bot Koruma:**\n• Ceza: `{BOT_CEZA_TURU.upper()}`\n• İzinli: `{len(IZINLI_BOTLAR)}`\n• Bot ID: `{bot.user.id}`",
            ephemeral=True)

@bot.tree.command(name="izinli_botlar", description="İzinli bot listesi")
@app_commands.default_permissions(administrator=True)
async def izinli_botlar(interaction):
    if not IZINLI_BOTLAR:
        await interaction.response.send_message("Boş.", ephemeral=True); return
    await interaction.response.send_message("\n".join([f"• `{b}`" for b in IZINLI_BOTLAR]), ephemeral=True)

# ========================================
# YARDIM
# ========================================
@bot.tree.command(name="yardim", description="Yardım menüsü")
async def yardim(interaction):
    embed = discord.Embed(title="🎯 Sancak RP Güvenlik Tanrısı", description="Tüm komutlar:", color=discord.Color.blue())
    embed.add_field(name="🛡️ GÜVENLİK", value="`/guard` `/guvenlik_log` `/guvenlik_durum` `/lockdown` `/unlock` `/idban` `/bot_ayar` `/izinli_botlar`", inline=False)
    embed.add_field(name="📝 Kayıt", value="`/kayitkur` `/karakterkur` `/arackur` `/iskur` `/ehliyetkur` `/silahkur` `/evkur` `/sikayetkur` `/yetkilikur` `/istekkur`", inline=False)
    embed.add_field(name="⚙️ Ayar", value="`/kayit_ayar` `/karakter_ayar` `/arac_ayar` `/is_ayar` `/ehliyet_ayar` `/silah_ayar` `/ev_ayar` `/sikayet_ayar` `/yetkili_ayar` `/istek_ayar`", inline=False)
    embed.add_field(name="🎫 Ticket", value="`/ticketkur`", inline=False)
    embed.add_field(name="🎭 Rol", value="`/rolver` `/rolal` `/toplurol`", inline=False)
    embed.add_field(name="⚖️ Moderasyon", value="`/ban` `/kick` `/ipban` `/unban` `/timeout` `/untimeout` `/uyari` `/uyarilar`", inline=False)
    embed.add_field(name="📊 İstatistik", value="`/profil` `/liderlik` `/gunluk`", inline=False)
    embed.add_field(name="🎉 Etkinlik", value="`/cekiliş` `/anket` `/duyuru`", inline=False)
    embed.add_field(name="⚙️ Yönetim", value="`/log_kanal` `/ticket_kategori` `/ayarlar`", inline=False)
    embed.add_field(name="🎲 Eğlence", value="`/zar` `/yazitura` `/espri`", inline=False)
    embed.set_footer(text="Sancak Roleplay • Güvenlik Tanrısı")
    await interaction.response.send_message(embed=embed)

# ========================================
# KAYIT SİSTEMLERİ
# ========================================

class KayitFormu(discord.ui.Modal, title="Sancak Roleplay - Whitelist"):
    soru1 = discord.ui.TextInput(label="1. Ad, Yaş, Kaynak", style=discord.TextStyle.short, required=True)
    soru2 = discord.ui.TextInput(label="2. Meta Gaming & Fail RP", style=discord.TextStyle.paragraph, required=True)
    soru3 = discord.ui.TextInput(label="3. IC & OOC", style=discord.TextStyle.paragraph, required=True)
    soru4 = discord.ui.TextInput(label="4. VDM & RDM", style=discord.TextStyle.paragraph, required=True)
    soru5 = discord.ui.TextInput(label="5. Örnek Kaza Rolü", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("kayit_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        e = discord.Embed(title="📝 Whitelist",
            description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.blue())
        e.add_field(name="1", value=self.soru1.value[:1024], inline=False)
        e.add_field(name="2", value=self.soru2.value[:1024], inline=False)
        e.add_field(name="3", value=self.soru3.value[:1024], inline=False)
        e.add_field(name="4", value=self.soru4.value[:1024], inline=False)
        e.add_field(name="5", value=self.soru5.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Whitelist")
        await log.send(embed=e, view=OnayView(interaction.user.id, "kayit"))
        await interaction.response.send_message("✅ Başvurunuz alındı!", ephemeral=True)

class OnayView(discord.ui.View):
    def __init__(self, uid, tip):
        super().__init__(timeout=None); self.uid = uid; self.tip = tip
    @discord.ui.button(label="Onayla", style=discord.ButtonStyle.success, emoji="✅")
    async def onayla(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
        uye = interaction.guild.get_member(self.uid)
        if not uye:
            await interaction.response.send_message("❌ Kullanıcı yok.", ephemeral=True); return
        rid = ayar_al(f"{self.tip}_verilecek_rol")
        try:
            if rid:
                r = interaction.guild.get_role(int(rid))
                if r: await uye.add_roles(r)
            await uye.send(f"🎉 Tebrikler! Sancak Roleplay {self.tip} başvurunuz onaylandı!")
        except: pass
        if self.tip == "karakter":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE karakterler SET durum='onaylandi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "arac":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE arac_kayit SET durum='onaylandi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "ehliyet":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE ehliyet SET durum='onaylandi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "silah":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE silah SET durum='onaylandi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "ev":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE ev SET durum='onaylandi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        emb = interaction.message.embeds[0]; emb.color = discord.Color.green()
        emb.set_footer(text=f"✅ Onaylayan: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message(f"✅ {uye.mention} onaylandı.", ephemeral=True)
    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reddet(self, interaction, button):
        if not yetkili_mi(interaction.user, KAYIT_YETKILI_ROLLER):
            await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
        uye = interaction.guild.get_member(self.uid)
        try:
            if uye: await uye.send(f"Üzgünüz, {self.tip} başvurunuz reddedildi.")
        except: pass
        if self.tip == "karakter":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE karakterler SET durum='reddedildi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "arac":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE arac_kayit SET durum='reddedildi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "ehliyet":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE ehliyet SET durum='reddedildi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "silah":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE silah SET durum='reddedildi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        elif self.tip == "ev":
            conn = db_baglan(); c = conn.cursor()
            c.execute("UPDATE ev SET durum='reddedildi' WHERE user_id=?", (self.uid,))
            conn.commit(); conn.close()
        emb = interaction.message.embeds[0]; emb.color = discord.Color.red()
        emb.set_footer(text=f"❌ Reddeden: {interaction.user.display_name}")
        await interaction.message.edit(embed=emb, view=None)
        await interaction.response.send_message("❌ Reddedildi.", ephemeral=True)

class KayitPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Kayıt Ol", style=discord.ButtonStyle.primary, emoji="➕", custom_id="kayit_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(KayitFormu())

@bot.tree.command(name="kayitkur", description="Kayıt paneli")
@app_commands.default_permissions(administrator=True)
async def kayitkur(interaction):
    e = discord.Embed(title="🎫 SANCAK ROLEPLAY KAYIT SİSTEMİ",
        description="**Hoş Geldiniz!**\n\nKayıt için butona tıklayın.",
        color=discord.Color.from_rgb(0, 102, 204))
    e.add_field(name="⚠️ Unutmayın", value="• 24 saat içinde incelenir.\n• Yanlış bilgi reddedilir.\n• Sonuç DM'den bildirilir.", inline=False)
    e.set_footer(text="Sancak Roleplay • Whitelist", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, KayitPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="kayit_ayar", description="Kayıt ayarları")
@app_commands.default_permissions(administrator=True)
async def kayit_ayar(interaction, log_kanal: discord.TextChannel, verilecek_rol: discord.Role):
    ayar_koy("kayit_log_kanal", log_kanal.id); ayar_koy("kayit_verilecek_rol", verilecek_rol.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# KARAKTER
class KarakterFormu(discord.ui.Modal, title="Sancak Roleplay - Karakter"):
    isim = discord.ui.TextInput(label="Karakter İsmi", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Karakter Yaşı", style=discord.TextStyle.short, required=True)
    meslek = discord.ui.TextInput(label="Meslek", style=discord.TextStyle.short, required=True)
    hikaye = discord.ui.TextInput(label="Hikaye", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("karakter_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO karakterler (user_id, isim, yas, meslek, hikaye, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, int(self.yas.value) if self.yas.value.isdigit() else 0, self.meslek.value, self.hikaye.value, "beklemede", datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="📝 Karakter Kaydı",
            description=f"**Başvuran:** {interaction.user.mention}\n**Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            color=discord.Color.purple())
        e.add_field(name="İsim", value=self.isim.value, inline=False)
        e.add_field(name="Yaş", value=self.yas.value, inline=True)
        e.add_field(name="Meslek", value=self.meslek.value, inline=True)
        e.add_field(name="Hikaye", value=self.hikaye.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Karakter")
        await log.send(embed=e, view=OnayView(interaction.user.id, "karakter"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class KarakterPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Karakter Kaydı", style=discord.ButtonStyle.primary, emoji="📝", custom_id="karakter_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(KarakterFormu())

@bot.tree.command(name="karakterkur", description="Karakter paneli")
@app_commands.default_permissions(administrator=True)
async def karakterkur(interaction):
    e = discord.Embed(title="🎮 SANCAK ROLEPLAY KARAKTER KAYIT",
        description="Karakter oluşturun.", color=discord.Color.purple())
    e.add_field(name="⚠️", value="• İsim RP kurallarına uygun.\n• Hikaye en az 3-4 cümle.", inline=False)
    e.set_footer(text="Sancak Roleplay • Karakter", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, KarakterPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="karakter_ayar", description="Karakter ayar")
@app_commands.default_permissions(administrator=True)
async def karakter_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("karakter_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

@bot.tree.command(name="karakter_bilgi", description="Karakter bilgisi")
async def karakter_bilgi(interaction, kullanici: discord.Member = None):
    if kullanici is None: kullanici = interaction.user
    conn = db_baglan(); c = conn.cursor()
    c.execute("SELECT isim, yas, meslek, hikaye, durum FROM karakterler WHERE user_id=?", (kullanici.id,))
    k = c.fetchone(); conn.close()
    if not k:
        await interaction.response.send_message(f"{kullanici.mention} karakter yok.", ephemeral=True); return
    e = discord.Embed(title=f"🎮 {kullanici.display_name}", color=discord.Color.purple())
    e.add_field(name="İsim", value=k[0]); e.add_field(name="Yaş", value=k[1])
    e.add_field(name="Meslek", value=k[2]); e.add_field(name="Durum", value=k[4])
    e.add_field(name="Hikaye", value=k[3][:1024], inline=False)
    await interaction.response.send_message(embed=e)

# ARAÇ
class AracFormu(discord.ui.Modal, title="Sancak Roleplay - Araç"):
    plaka = discord.ui.TextInput(label="Plaka", style=discord.TextStyle.short, required=True)
    marka = discord.ui.TextInput(label="Marka", style=discord.TextStyle.short, required=True)
    model = discord.ui.TextInput(label="Model", style=discord.TextStyle.short, required=True)
    renk = discord.ui.TextInput(label="Renk", style=discord.TextStyle.short, required=True)
    sahiplik = discord.ui.TextInput(label="Sahiplik", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("arac_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO arac_kayit (user_id, plaka, marka, model, renk, sahiplik, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.plaka.value, self.marka.value, self.model.value, self.renk.value, self.sahiplik.value, "beklemede", datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="🚗 Araç Kaydı",
            description=f"**Başvuran:** {interaction.user.mention}", color=discord.Color.dark_blue())
        e.add_field(name="Plaka", value=self.plaka.value, inline=True)
        e.add_field(name="Marka", value=self.marka.value, inline=True)
        e.add_field(name="Model", value=self.model.value, inline=True)
        e.add_field(name="Renk", value=self.renk.value, inline=True)
        e.add_field(name="Sahiplik", value=self.sahiplik.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Araç")
        await log.send(embed=e, view=OnayView(interaction.user.id, "arac"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class AracPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Araç Kaydı", style=discord.ButtonStyle.primary, emoji="🚗", custom_id="arac_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(AracFormu())

@bot.tree.command(name="arackur", description="Araç paneli")
@app_commands.default_permissions(administrator=True)
async def arackur(interaction):
    e = discord.Embed(title="🚗 SANCAK ROLEPLAY ARAÇ KAYIT",
        description="Araç kaydı yapın.", color=discord.Color.dark_blue())
    e.add_field(name="⚠️", value="• Çalıntı araç yasaktır.", inline=False)
    e.set_footer(text="Sancak Roleplay • Araç", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, AracPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="arac_ayar", description="Araç ayar")
@app_commands.default_permissions(administrator=True)
async def arac_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("arac_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# İŞ
class IsFormu(discord.ui.Modal, title="Sancak Roleplay - İş Başvurusu"):
    is_turu = discord.ui.TextInput(label="İş Türü", style=discord.TextStyle.short, required=True)
    isim = discord.ui.TextInput(label="Karakter İsmi", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Karakter Yaşı", style=discord.TextStyle.short, required=True)
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph, required=True)
    neden = discord.ui.TextInput(label="Neden?", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("is_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        icerik = f"İsim: {self.isim.value}\nYaş: {self.yas.value}\nDeneyim: {self.deneyim.value}\nNeden: {self.neden.value}"
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT INTO is_basvuru (user_id, is_turu, icerik, durum, tarih) VALUES (?, ?, ?, 'beklemede', ?)",
                  (interaction.user.id, self.is_turu.value, icerik, datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="💼 İş Başvurusu",
            description=f"**Başvuran:** {interaction.user.mention}", color=discord.Color.orange())
        e.add_field(name="İş", value=self.is_turu.value, inline=False)
        e.add_field(name="İsim", value=self.isim.value, inline=True)
        e.add_field(name="Yaş", value=self.yas.value, inline=True)
        e.add_field(name="Deneyim", value=self.deneyim.value[:1024], inline=False)
        e.add_field(name="Neden", value=self.neden.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • İş")
        await log.send(embed=e, view=OnayView(interaction.user.id, "is"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class IsPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="İş Başvurusu", style=discord.ButtonStyle.primary, emoji="💼", custom_id="is_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(IsFormu())

@bot.tree.command(name="iskur", description="İş paneli")
@app_commands.default_permissions(administrator=True)
async def iskur(interaction):
    e = discord.Embed(title="💼 SANCAK ROLEPLAY İŞ BAŞVURU",
        description="İş başvurusu yapın.", color=discord.Color.orange())
    e.add_field(name="📋 İşler", value="• 👮 Polis\n• 🚑 Doktor\n• 🔧 Teknik\n• 🕵️ Mafya", inline=False)
    e.set_footer(text="Sancak Roleplay • İş", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, IsPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="is_ayar", description="İş ayar")
@app_commands.default_permissions(administrator=True)
async def is_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("is_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# EHLİYET
class EhliyetFormu(discord.ui.Modal, title="Sancak Roleplay - Ehliyet"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Yaş", style=discord.TextStyle.short, required=True)
    ehliyet_turu = discord.ui.TextInput(label="Tür (A/B/C)", style=discord.TextStyle.short, required=True)
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("ehliyet_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ehliyet (user_id, isim, yas, ehliyet_turu, deneyim, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, self.yas.value, self.ehliyet_turu.value, self.deneyim.value, "beklemede", datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="🪪 Ehliyet Başvurusu",
            description=f"**Başvuran:** {interaction.user.mention}", color=discord.Color.teal())
        e.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        e.add_field(name="Yaş", value=self.yas.value, inline=True)
        e.add_field(name="Tür", value=self.ehliyet_turu.value, inline=True)
        e.add_field(name="Deneyim", value=self.deneyim.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Ehliyet")
        await log.send(embed=e, view=OnayView(interaction.user.id, "ehliyet"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class EhliyetPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Ehliyet Başvurusu", style=discord.ButtonStyle.primary, emoji="🪪", custom_id="ehliyet_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(EhliyetFormu())

@bot.tree.command(name="ehliyetkur", description="Ehliyet paneli")
@app_commands.default_permissions(administrator=True)
async def ehliyetkur(interaction):
    e = discord.Embed(title="🪪 SANCAK ROLEPLAY EHLİYET",
        description="Ehliyet başvurusu.", color=discord.Color.teal())
    e.add_field(name="📋", value="• 🏍️ A\n• 🚗 B\n• 🚚 C", inline=False)
    e.set_footer(text="Sancak Roleplay • Ehliyet", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, EhliyetPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="ehliyet_ayar", description="Ehliyet ayar")
@app_commands.default_permissions(administrator=True)
async def ehliyet_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("ehliyet_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# SİLAH
class SilahFormu(discord.ui.Modal, title="Sancak Roleplay - Silah Ruhsatı"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    silah_turu = discord.ui.TextInput(label="Silah Türü", style=discord.TextStyle.short, required=True)
    neden = discord.ui.TextInput(label="Neden?", style=discord.TextStyle.paragraph, required=True)
    gecmis = discord.ui.TextInput(label="Sabıka?", style=discord.TextStyle.short, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("silah_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO silah (user_id, isim, silah_turu, neden, gecmis, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, self.silah_turu.value, self.neden.value, self.gecmis.value, "beklemede", datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="🔫 Silah Ruhsatı",
            description=f"**Başvuran:** {interaction.user.mention}", color=discord.Color.dark_red())
        e.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        e.add_field(name="Silah", value=self.silah_turu.value, inline=True)
        e.add_field(name="Sabıka", value=self.gecmis.value, inline=True)
        e.add_field(name="Neden", value=self.neden.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Silah")
        await log.send(embed=e, view=OnayView(interaction.user.id, "silah"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class SilahPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Silah Ruhsatı", style=discord.ButtonStyle.primary, emoji="🔫", custom_id="silah_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(SilahFormu())

@bot.tree.command(name="silahkur", description="Silah paneli")
@app_commands.default_permissions(administrator=True)
async def silahkur(interaction):
    e = discord.Embed(title="🔫 SANCAK ROLEPLAY SİLAH RUHSATI",
        description="Ruhsat başvurusu.", color=discord.Color.dark_red())
    e.add_field(name="⚠️", value="• Ruhsatsız silah yasaktır.\n• Sabıka olanlar başvuramaz.", inline=False)
    e.set_footer(text="Sancak Roleplay • Silah", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, SilahPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="silah_ayar", description="Silah ayar")
@app_commands.default_permissions(administrator=True)
async def silah_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("silah_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# EV
class EvFormu(discord.ui.Modal, title="Sancak Roleplay - Ev"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    ev_adresi = discord.ui.TextInput(label="Adres", style=discord.TextStyle.short, required=True)
    ev_turu = discord.ui.TextInput(label="Tür", style=discord.TextStyle.short, required=True)
    fiyat = discord.ui.TextInput(label="Fiyat", style=discord.TextStyle.short, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("ev_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO ev (user_id, isim, ev_adresi, ev_turu, fiyat, durum, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (interaction.user.id, self.isim.value, self.ev_adresi.value, self.ev_turu.value, self.fiyat.value, "beklemede", datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="🏠 Ev Kaydı",
            description=f"**Başvuran:** {interaction.user.mention}", color=discord.Color.green())
        e.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        e.add_field(name="Adres", value=self.ev_adresi.value, inline=True)
        e.add_field(name="Tür", value=self.ev_turu.value, inline=True)
        e.add_field(name="Fiyat", value=self.fiyat.value, inline=True)
        e.set_footer(text="Sancak Roleplay • Ev")
        await log.send(embed=e, view=OnayView(interaction.user.id, "ev"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class EvPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Ev Kaydı", style=discord.ButtonStyle.primary, emoji="🏠", custom_id="ev_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(EvFormu())

@bot.tree.command(name="evkur", description="Ev paneli")
@app_commands.default_permissions(administrator=True)
async def evkur(interaction):
    e = discord.Embed(title="🏠 SANCAK ROLEPLAY EV KAYIT",
        description="Ev kaydı yapın.", color=discord.Color.green())
    e.add_field(name="📋", value="• 🏢 Daire\n• 🏡 Villa\n• 🏘️ Müstakil", inline=False)
    e.set_footer(text="Sancak Roleplay • Ev", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, EvPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="ev_ayar", description="Ev ayar")
@app_commands.default_permissions(administrator=True)
async def ev_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("ev_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# ŞİKAYET
class SikayetFormu(discord.ui.Modal, title="Sancak Roleplay - Şikayet"):
    sikayet_edilen = discord.ui.TextInput(label="Şikayet Edilen", style=discord.TextStyle.short, required=True)
    sebep = discord.ui.TextInput(label="Sebep", style=discord.TextStyle.paragraph, required=True)
    kanit = discord.ui.TextInput(label="Kanıt?", style=discord.TextStyle.paragraph, required=False)
    async def on_submit(self, interaction):
        log_id = ayar_al("sikayet_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT INTO sikayet (user_id, sikayet_edilen, sebep, kanit, durum, tarih) VALUES (?, ?, ?, ?, 'beklemede', ?)",
                  (interaction.user.id, self.sikayet_edilen.value, self.sebep.value, self.kanit.value or "", datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title="⚖️ Şikayet",
            description=f"**Şikayet Eden:** {interaction.user.mention}", color=discord.Color.dark_orange())
        e.add_field(name="Şikayet Edilen", value=self.sikayet_edilen.value, inline=False)
        e.add_field(name="Sebep", value=self.sebep.value[:1024], inline=False)
        e.add_field(name="Kanıt", value=(self.kanit.value or "Yok")[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Şikayet")
        await log.send(embed=e, view=OnayView(interaction.user.id, "sikayet"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class SikayetPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Şikayet Oluştur", style=discord.ButtonStyle.primary, emoji="⚖️", custom_id="sikayet_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(SikayetFormu())

@bot.tree.command(name="sikayetkur", description="Şikayet paneli")
@app_commands.default_permissions(administrator=True)
async def sikayetkur(interaction):
    e = discord.Embed(title="⚖️ SANCAK ROLEPLAY ŞİKAYET",
        description="Şikayet oluşturun.", color=discord.Color.dark_orange())
    e.add_field(name="⚠️", value="• Sahte şikayet ban sebebi.", inline=False)
    e.set_footer(text="Sancak Roleplay • Şikayet", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, SikayetPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="sikayet_ayar", description="Şikayet ayar")
@app_commands.default_permissions(administrator=True)
async def sikayet_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("sikayet_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# YETKİLİ
class YetkiliFormu(discord.ui.Modal, title="Sancak Roleplay - Yetkili Başvuru"):
    isim = discord.ui.TextInput(label="Ad Soyad", style=discord.TextStyle.short, required=True)
    yas = discord.ui.TextInput(label="Yaş", style=discord.TextStyle.short, required=True)
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph, required=True)
    neden = discord.ui.TextInput(label="Neden?", style=discord.TextStyle.paragraph, required=True)
    gunluk = discord.ui.TextInput(label="Günlük Aktiflik", style=discord.TextStyle.short, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("yetkili_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        e = discord.Embed(title="🛡️ Yetkili Başvurusu",
            description=f"**Başvuran:** {interaction.user.mention}", color=discord.Color.from_rgb(0, 200, 255))
        e.add_field(name="Ad Soyad", value=self.isim.value, inline=True)
        e.add_field(name="Yaş", value=self.yas.value, inline=True)
        e.add_field(name="Aktiflik", value=self.gunluk.value, inline=True)
        e.add_field(name="Deneyim", value=self.deneyim.value[:1024], inline=False)
        e.add_field(name="Neden", value=self.neden.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • Yetkili")
        await log.send(embed=e, view=OnayView(interaction.user.id, "yetkili"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class YetkiliPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Yetkili Başvurusu", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="yetkili_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(YetkiliFormu())

@bot.tree.command(name="yetkilikur", description="Yetkili paneli")
@app_commands.default_permissions(administrator=True)
async def yetkilikur(interaction):
    e = discord.Embed(title="🛡️ SANCAK ROLEPLAY YETKİLİ BAŞVURU",
        description="Yetkili olmak için başvurun.", color=discord.Color.from_rgb(0, 200, 255))
    e.add_field(name="⚠️", value="• En az 15 yaşında olun.\n• Günlük 2+ saat aktif olun.", inline=False)
    e.set_footer(text="Sancak Roleplay • Yetkili", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, YetkiliPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="yetkili_ayar", description="Yetkili ayar")
@app_commands.default_permissions(administrator=True)
async def yetkili_ayar(interaction, log_kanal: discord.TextChannel, verilecek_rol: discord.Role):
    ayar_koy("yetkili_log_kanal", log_kanal.id); ayar_koy("yetkili_verilecek_rol", verilecek_rol.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# İSTEK
class IstekFormu(discord.ui.Modal, title="Sancak Roleplay - İstek & Öneri"):
    tip = discord.ui.TextInput(label="Tip", style=discord.TextStyle.short, placeholder="İstek/Öneri/Şikayet", required=True)
    baslik = discord.ui.TextInput(label="Başlık", style=discord.TextStyle.short, required=True)
    icerik = discord.ui.TextInput(label="İçerik", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction):
        log_id = ayar_al("istek_log_kanal")
        if not log_id: await interaction.response.send_message("❌ Log yok!", ephemeral=True); return
        log = interaction.guild.get_channel(int(log_id))
        if not log: await interaction.response.send_message("❌ Kanal yok!", ephemeral=True); return
        conn = db_baglan(); c = conn.cursor()
        c.execute("INSERT INTO istek_oneri (user_id, tip, baslik, icerik, durum, tarih) VALUES (?, ?, ?, ?, 'beklemede', ?)",
                  (interaction.user.id, self.tip.value, self.baslik.value, self.icerik.value, datetime.now().isoformat()))
        conn.commit(); conn.close()
        e = discord.Embed(title=f"📩 {self.tip.value}",
            description=f"**Gönderen:** {interaction.user.mention}", color=discord.Color.from_rgb(255, 165, 0))
        e.add_field(name="Başlık", value=self.baslik.value[:1024], inline=False)
        e.add_field(name="İçerik", value=self.icerik.value[:1024], inline=False)
        e.set_footer(text="Sancak Roleplay • İstek")
        await log.send(embed=e, view=OnayView(interaction.user.id, "istek"))
        await interaction.response.send_message("✅ Alındı!", ephemeral=True)

class IstekPaneli(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="İstek / Öneri Gönder", style=discord.ButtonStyle.primary, emoji="📩", custom_id="istek_btn")
    async def k(self, interaction, b): await interaction.response.send_modal(IstekFormu())

@bot.tree.command(name="istekkur", description="İstek paneli")
@app_commands.default_permissions(administrator=True)
async def istekkur(interaction):
    e = discord.Embed(title="📩 SANCAK ROLEPLAY İSTEK & ÖNERİ",
        description="İstek/öneri gönderin.", color=discord.Color.from_rgb(255, 165, 0))
    e.add_field(name="💡", value="• 🎯 Fikirler\n• 🔧 Öneriler\n• 🐛 Hata\n• 📢 Şikayet", inline=False)
    e.set_footer(text="Sancak Roleplay • İstek", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, IstekPaneli())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="istek_ayar", description="İstek ayar")
@app_commands.default_permissions(administrator=True)
async def istek_ayar(interaction, log_kanal: discord.TextChannel):
    ayar_koy("istek_log_kanal", log_kanal.id)
    await interaction.response.send_message("✅ Ayarlandı.", ephemeral=True)

# ========================================
# TICKET
# ========================================
class TicketPanel(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Oyun İçi", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="t_oyun")
    async def o(self, i, b): await ticket_ac(i, "Oyun İçi")
    @discord.ui.button(label="Teknik", style=discord.ButtonStyle.secondary, emoji="🔧", custom_id="t_tek")
    async def t(self, i, b): await ticket_ac(i, "Teknik")
    @discord.ui.button(label="Donate", style=discord.ButtonStyle.success, emoji="🛒", custom_id="t_don")
    async def d(self, i, b): await ticket_ac(i, "Donate")
    @discord.ui.button(label="AntiCheat", style=discord.ButtonStyle.danger, emoji="🔨", custom_id="t_ac")
    async def a(self, i, b): await ticket_ac(i, "AntiCheat")

async def ticket_ac(interaction, kategori):
    guild = interaction.guild; user = interaction.user
    conn = db_baglan(); c = conn.cursor()
    c.execute("SELECT kanal_id FROM tickets WHERE kullanici_id = ? AND durum = 'acik'", (user.id,))
    if c.fetchone():
        await interaction.response.send_message("❌ Zaten ticketın var!", ephemeral=True); conn.close(); return
    kid = ayar_al("ticket_kategori")
    kk = guild.get_channel(int(kid)) if kid else None
    ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    for rn in TICKET_ROLLER:
        r = discord.utils.get(guild.roles, name=rn)
        if r: ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    sayi = len([k for k in guild.channels if k.name.startswith("ticket-")]) + 1
    kanal = await guild.create_text_channel(name=f"ticket-{sayi:04d}", category=kk, overwrites=ow)
    c.execute("INSERT INTO tickets (kanal_id, kullanici_id, konu, durum, tarih) VALUES (?, ?, ?, ?, ?)",
              (kanal.id, user.id, kategori, "acik", datetime.now().isoformat()))
    conn.commit(); conn.close()
    e = discord.Embed(title=f"🎫 Destek #{sayi:04d}", description=f"{user.mention} - **{kategori}**", color=discord.Color.blue())
    await kanal.send(content=user.mention, embed=e, view=TicketKontrol())
    await interaction.response.send_message(f"✅ {kanal.mention}", ephemeral=True)

class TicketKontrol(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Çözüldü", style=discord.ButtonStyle.success, emoji="✅", custom_id="t_coz")
    async def coz(self, i, b):
        conn = db_baglan(); c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (i.channel.id,))
        conn.commit(); conn.close()
        await i.response.send_message("✅ Kapatılıyor...")
        await asyncio.sleep(5); await i.channel.delete()
    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="t_kap")
    async def kap(self, i, b):
        conn = db_baglan(); c = conn.cursor()
        c.execute("UPDATE tickets SET durum = 'kapali' WHERE kanal_id = ?", (i.channel.id,))
        conn.commit(); conn.close()
        await i.response.send_message("🔒 Kapatılıyor...")
        await asyncio.sleep(3); await i.channel.delete()

@bot.tree.command(name="ticketkur", description="Ticket paneli")
@app_commands.default_permissions(administrator=True)
async def ticketkur(interaction):
    e = discord.Embed(title="🎫 SANCAK ROLEPLAY DESTEK",
        description="Destek talebi oluşturun.", color=discord.Color.blue())
    e.set_footer(text="Sancak Roleplay • Destek", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    await banner_gonder(interaction.channel, e, TicketPanel())
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

# ========================================
# MODERASYON
# ========================================
@bot.tree.command(name="ban", description="Ban atar")
async def ban(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await interaction.guild.ban(kullanici, reason=f"{sebep} | {interaction.user}")
    await interaction.response.send_message(embed=embed_yap("🔨 BAN", f"{kullanici.mention} banlandı.\n**Sebep:** {sebep}", discord.Color.dark_red()))

@bot.tree.command(name="kick", description="Kick atar")
async def kick(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await kullanici.kick(reason=f"{sebep} | {interaction.user}")
    await interaction.response.send_message(embed=embed_yap("👢 KICK", f"{kullanici.mention} atıldı.\n**Sebep:** {sebep}", discord.Color.orange()))

@bot.tree.command(name="ipban", description="IP ban atar")
async def ipban(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await interaction.guild.ban(kullanici, reason=f"[IP BAN] {sebep} | {interaction.user}")
    conn = db_baglan(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO ipbanlar (user_id, sebep, tarih, yetkili_id) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, datetime.now().isoformat(), interaction.user.id))
    conn.commit(); conn.close()
    await interaction.response.send_message(embed=embed_yap("🚫 IP BAN", f"{kullanici.mention}\n**Sebep:** {sebep}", discord.Color.dark_red()))

@bot.tree.command(name="unban", description="Ban kaldırır")
async def unban(interaction, kullanici_id: str):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    try:
        u = await bot.fetch_user(int(kullanici_id))
        await interaction.guild.unban(u)
        await interaction.response.send_message(f"✅ {u.mention} banı kaldırıldı.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Hata: {e}", ephemeral=True)

@bot.tree.command(name="timeout", description="Susturur")
async def timeout(interaction, kullanici: discord.Member, dakika: int, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await kullanici.timeout(timedelta(minutes=dakika), reason=sebep)
    await interaction.response.send_message(f"⏸️ {kullanici.mention} {dakika} dk susturuldu.")

@bot.tree.command(name="untimeout", description="Susturmayı kaldırır")
async def untimeout(interaction, kullanici: discord.Member):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await kullanici.timeout(None)
    await interaction.response.send_message(f"▶️ {kullanici.mention} açıldı.")

@bot.tree.command(name="uyari", description="Uyarı verir")
async def uyari(interaction, kullanici: discord.Member, sebep: str = "Belirtilmedi"):
    if not yetkili_mi(interaction.user, MOD_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    conn = db_baglan(); c = conn.cursor()
    c.execute("INSERT INTO uyarilar (user_id, sebep, yetkili_id, tarih) VALUES (?, ?, ?, ?)",
              (kullanici.id, sebep, interaction.user.id, datetime.now().isoformat()))
    c.execute("UPDATE uyeler SET uyari = uyari + 1 WHERE user_id = ?", (kullanici.id,))
    c.execute("SELECT COUNT(*) FROM uyarilar WHERE user_id = ?", (kullanici.id,))
    toplam = c.fetchone()[0]
    conn.commit(); conn.close()
    try:
        dm = discord.Embed(title="⚠️ UYARI ALDINIZ",
            description=f"**{interaction.guild.name}** sunucusunda uyarı aldınız.\n\n"
                        f"**Sebep:** {sebep}\n**Yetkili:** {interaction.user.display_name}\n**Toplam:** {toplam}",
            color=discord.Color.yellow())
        await kullanici.send(embed=dm)
        dm_d = "✅ Gönderildi"
    except: dm_d = "❌ Kapalı"
    e = discord.Embed(title="⚠️ UYARI VERİLDİ",
        description=f"**Kullanıcı:** {kullanici.mention}\n**Sebep:** {sebep}\n**Yetkili:** {interaction.user.mention}\n**Toplam:** {toplam}\n**DM:** {dm_d}",
        color=discord.Color.yellow())
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="uyarilar", description="Uyarıları gösterir")
async def uyarilar(interaction, kullanici: discord.Member):
    conn = db_baglan(); c = conn.cursor()
    c.execute("SELECT sebep, tarih FROM uyarilar WHERE user_id = ?", (kullanici.id,))
    ks = c.fetchall(); conn.close()
    if not ks:
        await interaction.response.send_message(f"Uyarı yok.", ephemeral=True); return
    m = "\n".join([f"• {s} ({t[:10]})" for s, t in ks])
    await interaction.response.send_message(embed=embed_yap(f"⚠️ {kullanici.display_name}", m, discord.Color.orange()))

# ========================================
# ROL
# ========================================
@bot.tree.command(name="rolver", description="Rol verir")
async def rolver(interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await kullanici.add_roles(rol)
    await interaction.response.send_message(embed=embed_yap("🎭 ROL VERİLDİ", f"{kullanici.mention} → {rol.mention}", discord.Color.green()))

@bot.tree.command(name="rolal", description="Rol alır")
async def rolal(interaction, kullanici: discord.Member, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await kullanici.remove_roles(rol)
    await interaction.response.send_message(embed=embed_yap("🎭 ROL ALINDI", f"{kullanici.mention} ← {rol.mention}", discord.Color.red()))

@bot.tree.command(name="toplurol", description="Tüm üyelere rol")
async def toplurol(interaction, rol: discord.Role):
    if not yetkili_mi(interaction.user, YETKILI_ROLLER):
        await interaction.response.send_message("❌ Yetki yok!", ephemeral=True); return
    await interaction.response.send_message(f"🎭 Veriliyor...", ephemeral=True)
    s = 0
    for u in interaction.guild.members:
        if u.bot: continue
        try:
            await u.add_roles(rol); s += 1; await asyncio.sleep(0.3)
        except: pass
    await interaction.channel.send(f"✅ {s} üyeye verildi.")

# ========================================
# İSTATİSTİK
# ========================================
@bot.tree.command(name="profil", description="Profil")
async def profil(interaction, kullanici: discord.Member = None):
    if kullanici is None: kullanici = interaction.user
    conn = db_baglan(); c = conn.cursor()
    c.execute("SELECT mesaj, xp, seviye, uyari FROM uyeler WHERE user_id = ?", (kullanici.id,))
    k = c.fetchone(); conn.close()
    m, xp, sv, uy = k if k else (0, 0, 1, 0)
    e = discord.Embed(title=f"👤 {kullanici.display_name}", color=discord.Color.blue())
    if kullanici.avatar: e.set_thumbnail(url=kullanici.avatar.url)
    e.add_field(name="📊 Mesaj", value=m); e.add_field(name="⭐ Seviye", value=sv)
    e.add_field(name="✨ XP", value=xp); e.add_field(name="⚠️ Uyarı", value=uy)
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="liderlik", description="Liderlik")
async def liderlik(interaction):
    conn = db_baglan(); c = conn.cursor()
    c.execute("SELECT user_id, mesaj, seviye FROM uyeler ORDER BY mesaj DESC LIMIT 10")
    ks = c.fetchall(); conn.close()
    m = ""
    for i, (uid, msj, sv) in enumerate(ks, 1):
        u = interaction.guild.get_member(uid)
        isim = u.display_name if u else f"ID: {uid}"
        m += f"**{i}.** {isim} - {msj} mesaj (Sv {sv})\n"
    await interaction.response.send_message(embed=embed_yap("🏆 Liderlik", m, discord.Color.gold()))

@bot.tree.command(name="gunluk", description="Günlük ödül")
async def gunluk(interaction):
    conn = db_baglan(); c = conn.cursor()
    bugun = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT son_gunluk FROM uyeler WHERE user_id = ?", (interaction.user.id,))
    k = c.fetchone()
    if k and k[0] == bugun:
        await interaction.response.send_message("⏳ Bugün aldın!", ephemeral=True); conn.close(); return
    o = random.randint(50, 200)
    c.execute("INSERT INTO uyeler (user_id, xp, son_gunluk) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET xp = xp + ?, son_gunluk = ?",
              (interaction.user.id, o, bugun, o, bugun))
    conn.commit(); conn.close()
    await interaction.response.send_message(embed=embed_yap("🎁 GÜNLÜK", f"**+{o} XP**", discord.Color.green()))

# ========================================
# ETKİNLİK
# ========================================
@bot.tree.command(name="duyuru", description="Duyuru")
@app_commands.default_permissions(administrator=True)
async def duyuru(interaction, baslik: str, mesaj: str):
    e = discord.Embed(title=f"📢 {baslik}", description=mesaj, color=discord.Color.red())
    e.set_footer(text="Sancak RP")
    await interaction.channel.send("@everyone", embed=e)
    await interaction.response.send_message("✅ Atıldı.", ephemeral=True)

@bot.tree.command(name="anket", description="Anket")
@app_commands.default_permissions(administrator=True)
async def anket(interaction, soru: str):
    e = discord.Embed(title="📊 Anket", description=soru, color=discord.Color.blue())
    m = await interaction.channel.send(embed=e)
    await m.add_reaction("✅"); await m.add_reaction("❌")
    await interaction.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="cekiliş", description="Çekiliş")
@app_commands.default_permissions(administrator=True)
async def cekilis(interaction, odul: str, sure: int):
    e = discord.Embed(title="🎉 ÇEKİLİŞ!",
        description=f"**Ödül:** {odul}\n**Süre:** {sure}s\n🎉 tıkla!", color=discord.Color.gold())
    m = await interaction.channel.send(embed=e)
    await m.add_reaction("🎉")
    await interaction.response.send_message("✅ Başladı.", ephemeral=True)
    await asyncio.sleep(sure)
    m = await interaction.channel.fetch_message(m.id)
    for r in m.reactions:
        if str(r.emoji) == "🎉":
            us = [u async for u in r.users() if not u.bot]
            if us:
                kz = random.choice(us)
                await interaction.channel.send(f"🎉 Tebrikler {kz.mention}! **{odul}**")

# ========================================
# YÖNETİM
# ========================================
@bot.tree.command(name="log_kanal", description="Log kanalı")
@app_commands.default_permissions(administrator=True)
async def log_kanal(interaction, kanal: discord.TextChannel):
    ayar_koy("log_kanal", kanal.id)
    await interaction.response.send_message(f"✅ {kanal.mention}", ephemeral=True)

@bot.tree.command(name="ticket_kategori", description="Ticket kategori")
@app_commands.default_permissions(administrator=True)
async def ticket_kategori(interaction, kategori: discord.CategoryChannel):
    ayar_koy("ticket_kategori", kategori.id)
    await interaction.response.send_message(f"✅ {kategori.name}", ephemeral=True)

@bot.tree.command(name="ayarlar", description="Ayarlar")
async def ayarlar(interaction):
    e = discord.Embed(title="⚙️ Sancak RP Ayarlar", color=discord.Color.blue())
    for a, i in [("log_kanal", "Log"), ("guvenlik_log_kanal", "Güvenlik Log"),
                 ("ticket_kategori", "Ticket Kat"), ("kayit_log_kanal", "Kayıt Log"),
                 ("kayit_verilecek_rol", "Kayıt Rol"), ("karakter_log_kanal", "Karakter"),
                 ("arac_log_kanal", "Araç"), ("is_log_kanal", "İş"),
                 ("ehliyet_log_kanal", "Ehliyet"), ("silah_log_kanal", "Silah"),
                 ("ev_log_kanal", "Ev"), ("sikayet_log_kanal", "Şikayet"),
                 ("yetkili_log_kanal", "Yetkili Log"), ("yetkili_verilecek_rol", "Yetkili Rol"),
                 ("istek_log_kanal", "İstek Log")]:
        d = ayar_al(a, "Ayarlanmadı")
        if d != "Ayarlanmadı" and "rol" in a:
            e.add_field(name=i, value=f"<@&{d}>", inline=True)
        elif d != "Ayarlanmadı":
            e.add_field(name=i, value=f"<#{d}>", inline=True)
        else:
            e.add_field(name=i, value=d, inline=True)
    await interaction.response.send_message(embed=e)

# ========================================
# EĞLENCE
# ========================================
@bot.tree.command(name="zar", description="Zar")
async def zar(interaction): await interaction.response.send_message(f"🎲 **{random.randint(1, 6)}**")

@bot.tree.command(name="yazitura", description="Yazı tura")
async def yazitura(interaction): await interaction.response.send_message(f"🪙 **{random.choice(['Yazı', 'Tura'])}**")

@bot.tree.command(name="espri", description="Espri")
async def espri(interaction): await interaction.response.send_message(f"😂 {random.choice(['Sinüsleri var.', 'Antivirüs var.', 'Bug var.'])}")

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
