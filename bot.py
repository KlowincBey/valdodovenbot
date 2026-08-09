import discord
from discord.ext import commands
import asyncio
import os
import random
import aiohttp
import io
import json
from datetime import datetime
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

# ==========================================
# self_bot=True ile başlatılıyor (normal botla karışmasın diye)
# ==========================================
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None, self_bot=True)

spam_aktif = False
silme_aktif = False

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!yardım"))
    print(f'✅ Bot hazır: {bot.user} (Self-Bot modu: {bot.self_bot})')

@bot.event
async def on_command_error(ctx, error):
    print(f"Hata: {error}")
    await ctx.send(f"❌ Hata: {str(error)[:100]}")

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

# ==========================================
# SELF-BOT KOMUTLARI (Kendi hesabınla çalışır)
# ==========================================

@bot.command()
async def selfspam(ctx, miktar: int = 5):
    """Kendi hesabınla spam atar (self-bot)."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    await ctx.send(f"⚠️ {miktar} mesaj gönderiliyor...")
    for i in range(miktar):
        await ctx.send(f"**{i+1}. Test mesajı**")
        await asyncio.sleep(0.3)
    await ctx.send("✅ Spam tamamlandı!")

@bot.command()
async def selfsil(ctx, miktar: int = 10):
    """Kendi mesajlarını siler (self-bot)."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    await ctx.send(f"🗑️ Son {miktar} mesaj siliniyor...")
    sayac = 0
    async for msg in ctx.channel.history(limit=miktar):
        if msg.author == bot.user:
            await msg.delete()
            sayac += 1
            await asyncio.sleep(0.2)
    await ctx.send(f"✅ {sayac} mesaj silindi!")

@bot.command()
async def selfeveryone(ctx, *, mesaj):
    """Kendi hesabınla @everyone mesajı atar."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    await ctx.send(f"@everyone {mesaj}")

@bot.command()
async def selfdm(ctx, member: discord.Member, *, mesaj):
    """Kendi hesabından DM gönderir."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    try:
        await member.send(mesaj)
        await ctx.send(f"✅ {member.mention} adlı kişiye DM gönderildi!")
    except:
        await ctx.send(f"❌ {member.mention} adlı kişiye DM gönderilemedi.")

@bot.command()
async def selfmesajsil(ctx, miktar: int = 10):
    """Herhangi birinin mesajlarını siler (self-bot)."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    await ctx.send(f"🗑️ Son {miktar} mesaj siliniyor...")
    sayac = 0
    async for msg in ctx.channel.history(limit=miktar):
        try:
            await msg.delete()
            sayac += 1
            await asyncio.sleep(0.2)
        except:
            pass
    await ctx.send(f"✅ {sayac} mesaj silindi!")

@bot.command()
async def selfkanalkopyala(ctx, kanal_id: int):
    """Başka bir kanaldaki son 10 mesajı bu kanala kopyalar."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    hedef_kanal = bot.get_channel(kanal_id)
    if not hedef_kanal:
        await ctx.send("❌ Kanal bulunamadı!")
        return
    await ctx.send(f"📋 {hedef_kanal.name} kanalından mesajlar kopyalanıyor...")
    sayac = 0
    async for msg in hedef_kanal.history(limit=10):
        try:
            await ctx.send(f"**{msg.author}:** {msg.content}")
            sayac += 1
            await asyncio.sleep(0.3)
        except:
            pass
    await ctx.send(f"✅ {sayac} mesaj kopyalandı!")

@bot.command()
async def selfbottoken(ctx):
    """Token'ını gösterir (self-bot)."""
    if not bot.self_bot:
        await ctx.send("❌ Bu komut sadece self-bot modunda çalışır!")
        return
    await ctx.send(f"🔑 Token: `{bot.http.token}`")

# ==========================================
# NORMAL YIKIM KOMUTLARI (Yetki Gerektirir)
# ==========================================

@bot.command()
async def sl(ctx):
    global silme_aktif
    if silme_aktif:
        await ctx.send("⚠️ Zaten silme işlemi aktif.")
        return
    silme_aktif = True
    await ctx.send("🗑️ Tüm kanallar 0.3 saniye arayla siliniyor... (!sildur ile durdur)")
    for kanal in ctx.guild.channels:
        if not silme_aktif:
            break
        try:
            await kanal.delete()
            await asyncio.sleep(0.3)
        except:
            pass
    silme_aktif = False
    await ctx.send("✅ Kanallar silme işlemi tamamlandı veya durduruldu.")

@bot.command()
async def sildur(ctx):
    global silme_aktif
    silme_aktif = False
    await ctx.send("🛑 Kanal silme durduruldu.")

@bot.command()
async def slhepsi(ctx):
    await ctx.send("💥 Tüm kanallar tek seferde siliniyor...")
    kanallar = ctx.guild.channels
    basarili = 0
    basarisiz = 0
    for kanal in kanallar:
        try:
            await kanal.delete()
            basarili += 1
        except:
            basarisiz += 1
    await ctx.send(f"✅ **{basarili}** kanal silindi.\n❌ **{basarisiz}** kanal silinemedi.")

@bot.command()
async def spamwebhook(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("⚠️ Zaten spam aktif.")
        return
    await ctx.send("🔧 Webhook'lar oluşturuluyor...")
    webhooklar = []
    for kanal in ctx.guild.text_channels:
        try:
            webhook = await kanal.create_webhook(name="SpamBot")
            webhooklar.append(webhook)
        except:
            pass
    if not webhooklar:
        await ctx.send("❌ Hiçbir kanala webhook oluşturulamadı!")
        return
    spam_aktif = True
    await ctx.send(f"⚡ SÜPER HIZLI webhook spam başladı! {len(webhooklar)} webhook ile (!dur ile durdur)")
    sayac = 0
    while spam_aktif:
        for i in range(0, len(webhooklar), 5):
            if not spam_aktif:
                break
            grup = webhooklar[i:i+5]
            tasks = []
            for webhook in grup:
                tasks.append(webhook.send("@everyone **Valdo/Klowinc Siker .d**", username="Valdo/Klowinc"))
            await asyncio.gather(*tasks, return_exceptions=True)
            sayac += len(grup)
            await asyncio.sleep(0.3)
        if sayac % 50 == 0:
            await ctx.send(f"📊 {sayac} mesaj gönderildi!")
    for webhook in webhooklar:
        try:
            await webhook.delete()
        except:
            pass
    await ctx.send(f"✅ Spam durduruldu! Toplam {sayac} mesaj gönderildi.")

@bot.command()
async def spam(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("⚠️ Zaten spam aktif.")
        return
    spam_aktif = True
    await ctx.send("🔊 Hızlı spam başladı! (!dur ile durdur)")
    while spam_aktif:
        tasks = []
        for kanal in ctx.guild.text_channels:
            tasks.append(kanal.send("@everyone **Valdo/Klowinc Siker .d**"))
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.5)
    await ctx.send("✅ Spam durduruldu.")

@bot.command()
async def spamyavas(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("⚠️ Zaten spam aktif.")
        return
    spam_aktif = True
    await ctx.send("🐢 Yavaş spam başladı! (!dur ile durdur)")
    while spam_aktif:
        for kanal in ctx.guild.text_channels:
            if not spam_aktif:
                break
            try:
                await kanal.send("@everyone **Valdo/Klowinc Siker .d**")
            except:
                pass
        await asyncio.sleep(0.5)
    await ctx.send("✅ Spam durduruldu.")

@bot.command()
async def dur(ctx):
    global spam_aktif
    spam_aktif = False
    await ctx.send("🛑 Spam durduruldu.")

@bot.command()
async def roluştur(ctx, *, isim):
    try:
        rol = await ctx.guild.create_role(name=isim)
        await ctx.send(f"✅ `{rol.name}` adlı rol oluşturuldu!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def rolsil(ctx, rol: discord.Role):
    try:
        await rol.delete()
        await ctx.send(f"✅ `{rol.name}` adlı rol silindi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def rolver(ctx, member: discord.Member, rol: discord.Role):
    try:
        await member.add_roles(rol)
        await ctx.send(f"✅ {member.mention} adlı kişiye `{rol.name}` rolü verildi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def rolat(ctx, member: discord.Member, rol: discord.Role):
    try:
        await member.remove_roles(rol)
        await ctx.send(f"✅ {member.mention} adlı kişiden `{rol.name}` rolü alındı!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def everyone(ctx, *, mesaj):
    await ctx.send(f"@everyone {mesaj}")

@bot.command()
async def dm(ctx, member: discord.Member, *, mesaj):
    try:
        await member.send(mesaj)
        await ctx.send(f"✅ {member.mention} adlı kişiye DM gönderildi!")
    except:
        await ctx.send(f"❌ {member.mention} adlı kişiye DM gönderilemedi.")

@bot.command()
async def kanalkilit(ctx):
    for kanal in ctx.guild.text_channels:
        try:
            await kanal.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    await ctx.send("🔒 Tüm kanallar kilitlendi!")

@bot.command()
async def kanalaç(ctx):
    for kanal in ctx.guild.text_channels:
        try:
            await kanal.set_permissions(ctx.guild.default_role, send_messages=None)
        except:
            pass
    await ctx.send("🔓 Tüm kanalların kilidi açıldı!")

@bot.command()
async def kanaloluştur(ctx, *, isim):
    try:
        await ctx.guild.create_text_channel(isim)
        await ctx.send(f"✅ `{isim}` adlı kanal oluşturuldu!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def kanalsil(ctx, kanal: discord.TextChannel):
    try:
        await kanal.delete()
        await ctx.send(f"✅ `{kanal.name}` adlı kanal silindi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def kategorisil(ctx, kategori_adi: str):
    kategori = discord.utils.get(ctx.guild.categories, name=kategori_adi)
    if not kategori:
        await ctx.send("❌ Böyle bir kategori bulunamadı!")
        return
    sayac = 0
    for kanal in kategori.channels:
        try:
            await kanal.delete()
            sayac += 1
        except:
            pass
    await kategori.delete()
    await ctx.send(f"✅ `{kategori_adi}` kategorisi ve {sayac} kanal silindi!")

@bot.command()
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
    await ctx.send(f"✅ {sayac} rol silindi!")

@bot.command()
async def sunucubosalt(ctx):
    await ctx.send("💀 Tüm üyeler banlanıyor...")
    sayac = 0
    for member in ctx.guild.members:
        if member == ctx.author or member == ctx.guild.me:
            continue
        try:
            await member.ban(reason="Sunucu boşaltma işlemi")
            sayac += 1
        except:
            pass
    await ctx.send(f"✅ {sayac} üye banlandı!")

@bot.command()
async def rastgeleat(ctx, sayi: int = 1):
    uyeler = [uye for uye in ctx.guild.members if not uye.bot and uye != ctx.author]
    if len(uyeler) < sayi:
        await ctx.send("❌ Yeterli üye yok!")
        return
    secilen = random.sample(uyeler, sayi)
    sayac = 0
    for uye in secilen:
        try:
            await uye.kick(reason="Rastgele atma işlemi")
            sayac += 1
        except:
            pass
    await ctx.send(f"✅ {sayac} üye rastgele atıldı!")

@bot.command()
async def kanalpatlat(ctx, sayi: int, *, isim: str = "patlama"):
    sayac = 0
    await ctx.send(f"🔨 {sayi} kanal oluşturuluyor...")
    for i in range(sayi):
        try:
            await ctx.guild.create_text_channel(f"{isim}-{i+1}")
            sayac += 1
        except:
            pass
    await ctx.send(f"✅ {sayac} kanal oluşturuldu!")

@bot.command()
async def sunucuismi(ctx, *, yeni_isim):
    try:
        await ctx.guild.edit(name=yeni_isim)
        await ctx.send(f"✅ Sunucu ismi `{yeni_isim}` olarak değiştirildi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def sunucuyedekle(ctx):
    await ctx.send("📦 Sunucu yedekleniyor...")
    veri = {
        "sunucu_ismi": ctx.guild.name,
        "sunucu_id": ctx.guild.id,
        "kanallar": [],
        "roller": []
    }
    for kanal in ctx.guild.channels:
        kanal_verisi = {
            "isim": kanal.name,
            "id": kanal.id,
            "tip": str(kanal.type),
            "konum": kanal.position,
            "kategori": kanal.category.name if kanal.category else None,
            "izinler": {}
        }
        try:
            for overwrite in kanal.overwrites:
                hedef = overwrite[0]
                izinler = overwrite[1]
                if isinstance(hedef, discord.Role):
                    kanal_verisi["izinler"][f"rol_{hedef.id}"] = {
                        "allow": izinler.pair()[0].value,
                        "deny": izinler.pair()[1].value
                    }
                elif isinstance(hedef, discord.Member):
                    kanal_verisi["izinler"][f"uye_{hedef.id}"] = {
                        "allow": izinler.pair()[0].value,
                        "deny": izinler.pair()[1].value
                    }
        except:
            pass
        veri["kanallar"].append(kanal_verisi)
    for rol in ctx.guild.roles:
        try:
            rol_verisi = {
                "isim": rol.name,
                "id": rol.id,
                "renk": str(rol.color),
                "konum": rol.position,
                "ayri": rol.hoist if hasattr(rol, 'hoist') else False,
                "bahsedilebilir": rol.mentionable if hasattr(rol, 'mentionable') else False,
                "yetkiler": rol.permissions.value,
                "uye_sayisi": len(rol.members)
            }
            veri["roller"].append(rol_verisi)
        except:
            pass
    dosya_adi = f"yedek_{ctx.guild.id}.json"
    with open(dosya_adi, "w", encoding="utf-8") as f:
        json.dump(veri, f, indent=2, ensure_ascii=False)
    await ctx.send(file=discord.File(dosya_adi))
    os.remove(dosya_adi)
    await ctx.send("✅ Sunucu yedeklendi!")

@bot.command()
async def yedektenyukle(ctx):
    if not ctx.message.attachments:
        await ctx.send("❌ Lütfen bir yedek JSON dosyası gönder!")
        return
    dosya = ctx.message.attachments[0]
    if not dosya.filename.endswith('.json'):
        await ctx.send("❌ Lütfen geçerli bir JSON dosyası gönder!")
        return
    await ctx.send("🔄 Sunucu geri yükleniyor... Bu biraz zaman alabilir!")
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
                    hoist=rol_verisi.get("ayri", False),
                    mentionable=rol_verisi.get("bahsedilebilir", False),
                    permissions=discord.Permissions(rol_verisi.get("yetkiler", 0))
                )
                yeni_roller[rol_verisi["id"]] = yeni_rol
            except:
                pass
        for kanal_verisi in yedek["kanallar"]:
            try:
                tip = kanal_verisi["tip"]
                if tip == "text":
                    yeni_kanal = await ctx.guild.create_text_channel(kanal_verisi["isim"], position=kanal_verisi.get("konum", 0))
                elif tip == "voice":
                    yeni_kanal = await ctx.guild.create_voice_channel(kanal_verisi["isim"], position=kanal_verisi.get("konum", 0))
                elif tip == "category":
                    yeni_kanal = await ctx.guild.create_category(kanal_verisi["isim"])
                else:
                    continue
                for izin_anahtar, izin_verisi in kanal_verisi.get("izinler", {}).items():
                    try:
                        if izin_anahtar.startswith("rol_"):
                            rol_id = int(izin_anahtar.split("_")[1])
                            hedef_rol = yeni_roller.get(rol_id)
                            if hedef_rol:
                                await yeni_kanal.set_permissions(
                                    hedef_rol,
                                    allow=discord.Permissions(izin_verisi["allow"]),
                                    deny=discord.Permissions(izin_verisi["deny"])
                                )
                    except:
                        pass
            except:
                pass
        await ctx.send("✅ Sunucu başarıyla geri yüklendi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def rolyetkisi(ctx, rol_id: int, *, yetki_adi: str):
    rol = ctx.guild.get_role(rol_id)
    if not rol:
        await ctx.send("❌ Bu ID'ye sahip bir rol bulunamadı!")
        return
    yetkiler = {
        "admin": discord.Permissions(administrator=True),
        "ban": discord.Permissions(ban_members=True),
        "kick": discord.Permissions(kick_members=True),
        "yonetici": discord.Permissions(administrator=True),
        "kanal_yonet": discord.Permissions(manage_channels=True),
        "rol_yonet": discord.Permissions(manage_roles=True),
        "mesaj_sil": discord.Permissions(manage_messages=True),
        "webhook": discord.Permissions(manage_webhooks=True),
        "hersey": discord.Permissions.all_permissions()
    }
    if yetki_adi.lower() in yetkiler:
        await rol.edit(permissions=yetkiler[yetki_adi.lower()])
        await ctx.send(f"✅ `{rol.name}` rolüne `{yetki_adi}` yetkisi verildi!")
    else:
        await ctx.send(f"❌ Geçersiz yetki! Kullanılabilir yetkiler: {', '.join(yetkiler.keys())}")

@bot.command()
async def servericon(ctx):
    if not ctx.message.attachments:
        await ctx.send("❌ Lütfen bir resim dosyası gönder!")
        return
    dosya = ctx.message.attachments[0]
    if not dosya.content_type.startswith('image/'):
        await ctx.send("❌ Lütfen geçerli bir resim dosyası gönder!")
        return
    try:
        resim = await dosya.read()
        await ctx.guild.edit(icon=resim)
        await ctx.send("✅ Sunucu profil fotoğrafı başarıyla değiştirildi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def servername(ctx, *, yeni_isim):
    try:
        await ctx.guild.edit(name=yeni_isim)
        await ctx.send(f"✅ Sunucu ismi başarıyla **{yeni_isim}** olarak değiştirildi!")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def sıfırla(ctx):
    await ctx.send("☢️ **SUNUCU SIFIRLANIYOR!** Bu işlem geri alınamaz. Tüm kanallar, roller ve üyeler silinecek/banlanacak.\n\n**Devam etmek için 10 saniye içinde `evet` yazın.**")
    def onay_kontrol(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "evet"
    try:
        await bot.wait_for('message', timeout=10.0, check=onay_kontrol)
    except asyncio.TimeoutError:
        await ctx.send("⏰ İşlem iptal edildi.")
        return
    await ctx.send("💥 **SUNUCU SIFIRLANIYOR...**")
    kanal_sayac = 0
    for kanal in ctx.guild.channels:
        try:
            await kanal.delete()
            kanal_sayac += 1
        except:
            pass
    rol_sayac = 0
    for rol in ctx.guild.roles:
        if rol.name != "@everyone":
            try:
                await rol.delete()
                rol_sayac += 1
            except:
                pass
    uye_sayac = 0
    for member in ctx.guild.members:
        if member == ctx.guild.me or member == ctx.author:
            continue
        try:
            await member.ban(reason="Sunucu sıfırlama işlemi")
            uye_sayac += 1
        except:
            pass
    try:
        await ctx.guild.edit(name="🔥 SIFIRLANDI")
    except:
        pass
    try:
        yeni_kanal = await ctx.guild.create_text_channel("sifirlandi")
        await yeni_kanal.send(
            f"💀 **SUNUCU SIFIRLANDI!**\n\n"
            f"✅ **{kanal_sayac}** kanal silindi.\n"
            f"✅ **{rol_sayac}** rol silindi.\n"
            f"✅ **{uye_sayac}** üye banlandı.\n\n"
            f"Sunucu sıfırlandı. Geriye sadece sen kaldın, kral! 👑"
        )
    except:
        print("Sunucu sıfırlandı.")

# ==========================================
# EĞLENCE KOMUTLARI (Eskiler)
# ==========================================

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
        await ctx.send("❌ ataturk.jpg bulunamadı.")

@bot.command()
async def furkandomalma(ctx):
    try:
        await ctx.send(file=discord.File('furkandomalma.jpg'))
    except:
        await ctx.send("❌ furkandomalma.jpg bulunamadı.")

@bot.command()
async def furkanvideo(ctx):
    try:
        await ctx.send(file=discord.File('furkan.mp4'))
    except:
        await ctx.send("❌ furkan.mp4 bulunamadı.")

@bot.command()
async def zar(ctx):
    sonuc = random.randint(1, 6)
    zar_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    embed = discord.Embed(title="🎲 Zar", description=f"**{sonuc}** {zar_emoji[sonuc-1]}", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def yazitura(ctx):
    sonuc = random.choice(["Yazı", "Tura"])
    embed = discord.Embed(title="🪙 Yazı Tura", description=f"**{sonuc}**", color=discord.Color.green())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def şanslısayı(ctx):
    sayi = random.randint(1, 100)
    embed = discord.Embed(title="🍀 Şanslı Sayın", description=f"**{sayi}**", color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def korkut(ctx):
    korkular = ["👻 Arkanda biri var!", "💀 Gece yarısı kapını çalacaklar...", "🔪 Sessiz ol, seni izliyorlar!", "🕷️ Yatağının altında bir şey var...", "🧟 Zombi saldırısı başladı!", "👽 Uzaylılar geldi, kaç!"]
    embed = discord.Embed(title="👻 KORKU", description=random.choice(korkular), color=discord.Color.dark_red())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def aşkfalı(ctx, *, isim=None):
    if isim is None:
        isim = ctx.author.display_name
    uyeler = [uye for uye in ctx.guild.members if not uye.bot and uye != ctx.author]
    if not uyeler:
        await ctx.send("❌ Yeterli üye yok.")
        return
    secilen = random.choice(uyeler)
    yorumlar = [
        f"{isim}, bu hafta aşk hayatında sürpriz bir gelişme olacak! Belki de **{secilen.display_name}** ile aranda bir şeyler olabilir.",
        f"{isim}, kalbinin sesini dinle, doğru kişi yakında. **{secilen.display_name}**'e dikkat et.",
        f"{isim}, eski bir aşk yeniden ortaya çıkabilir. Ama **{secilen.display_name}** yeni bir umut.",
        f"{isim}, bu ay yalnız kalmayacaksın, **{secilen.display_name}** ile tanışacaksın.",
        f"{isim}, aşk falına göre çok yakında kalbin pır pır edecek. **{secilen.display_name}** kalbini çalabilir."
    ]
    embed = discord.Embed(title="🔮 Aşk Falı", description=random.choice(yorumlar), color=discord.Color.magenta())
    embed.set_thumbnail(url=secilen.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def tarih(ctx):
    now = datetime.now()
    tarih_str = now.strftime("%d %B %Y, %A")
    ozel_gunler = {
        "01-01": "Yılbaşı! 🎉",
        "04-23": "23 Nisan Ulusal Egemenlik ve Çocuk Bayramı! 🇹🇷",
        "05-19": "19 Mayıs Gençlik ve Spor Bayramı! 🇹🇷",
        "07-15": "15 Temmuz Demokrasi ve Milli Birlik Günü! 🇹🇷",
        "08-30": "30 Ağustos Zafer Bayramı! 🇹🇷",
        "10-29": "29 Ekim Cumhuriyet Bayramı! 🇹🇷",
        "11-10": "10 Kasım Atatürk'ü Anma Günü 🇹🇷",
        "12-31": "Yılbaşı arifesi! 🎆"
    }
    key = now.strftime("%m-%d")
    ozel = ozel_gunler.get(key, "Bugün özel bir gün değil.")
    embed = discord.Embed(title="📅 Tarih", description=f"**{tarih_str}**\n{ozel}", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Gecikme: **{latency}ms**", color=discord.Color.green())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kullanıcıbilgi(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"📋 {member.display_name} Hakkında", color=discord.Color.blue())
    embed.add_field(name="Kullanıcı Adı", value=member.name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Hesap Açılış", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Sunucuya Katılış", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Roller", value=", ".join([rol.name for rol in member.roles if rol.name != "@everyone"]) or "Yok", inline=False)
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def ship(ctx, kisi1: discord.Member, kisi2: discord.Member = None):
    if kisi2 is None:
        uyeler = [uye for uye in ctx.guild.members if not uye.bot and uye != kisi1]
        if not uyeler:
            await ctx.send("❌ Yeterli üye yok.")
            return
        kisi2 = random.choice(uyeler)
    uyum = random.randint(0, 100)
    try:
        img_bytes = await birlestir_avatar(ctx, kisi1, kisi2, uyum)
        dosya = discord.File(img_bytes, filename="ship.png")
        embed = discord.Embed(title="💞 AŞK UYUMU", color=discord.Color.red())
        embed.set_image(url="attachment://ship.png")
        embed.set_footer(text=f"{kisi1.display_name} ❤️ {kisi2.display_name}")
        await ctx.send(file=dosya, embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Görsel oluşturulamadı: {e}")

@bot.command()
async def eightball(ctx, *, soru):
    cevaplar = [
        "Evet", "Hayır", "Belki", "Kesinlikle", "Asla", 
        "Olabilir", "Şanslısın", "Denemeye değer", "Unut gitsin", 
        "Yarın tekrar sor", "Kesinlikle hayır", "Kesinlikle evet"
    ]
    embed = discord.Embed(title="🎱 Sihirli 8 Top", description=f"Soru: **{soru}**\nCevap: **{random.choice(cevaplar)}**", color=discord.Color.purple())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def espri(ctx):
    espiriler = [
        "Bir gün bir bilgisayar virüsü hastaneye gitmiş. Doktor: 'Geçmiş olsun, sende antivirüs var!'",
        "Neden matematikçiler denizde yüzemez? Çünkü sinüsleri var.",
        "Bugün çok mutluyum, çünkü hayatımda ilk defa bir bot bana '!espri' dedi.",
        "İki programcı arasında geçen diyalog: 'Neden kodun çalışmıyor?' 'Bilmiyorum, belki de syntax hatası var.' 'Ya da belki senin beyninde bug var.'",
        "Bir inek, bir tavuk ve bir at konuşuyormuş. İnek: 'Ben süt veriyorum.' Tavuk: 'Ben yumurta veriyorum.' At: 'Ben de sosyal medyada 'harika' yorumları alıyorum.'"
    ]
    embed = discord.Embed(title="😂 Espri", description=random.choice(espiriler), color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def fbi(ctx):
    embed = discord.Embed(title="🚨 FBI! AÇIL!", description="Eller yukarı! 📸", color=discord.Color.dark_red())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"{member.display_name}'in avatarı")
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kompliman(ctx):
    komplimanlar = [
        "Çok güzel gülüyorsun!", "Zekanla herkesi büyülüyorsun!", "Bugün çok iyi görünüyorsun!",
        "Seninle sohbet etmek çok keyifli!", "Ne kadar ilham verici bir insansın!",
        "Gülüşün dünyayı aydınlatıyor!", "Çok yeteneklisin, bunu biliyorsun değil mi?",
        "İyi kalbin herkes tarafından görülüyor!", "Her zamanki gibi harikasın!",
        "Sen bir yıldızsın!", "Dünyanın en iyi insanısın!"
    ]
    embed = discord.Embed(title="💬 Kompliman", description=random.choice(komplimanlar), color=discord.Color.pink())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def hakaret(ctx):
    hakaretler = [
        "Seni gidi seni!", "Biraz daha efor sarf et!", "Ne kadar da sıradansın!",
        "Bunu daha iyi yapabilirsin biliyorum!", "Yeteneklerini geliştirmen şart!",
        "Seni seviyorum ama bu seferlik!", "Farklı olmaya çalış bari!",
        "Bazen çok yorucu olabiliyorsun!", "Düşünce tarzın ilginç!", "Kendine biraz çeki düzen ver!"
    ]
    embed = discord.Embed(title="😜 Şaka Hakaret", description=random.choice(hakaretler), color=discord.Color.orange())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def yılankavi(ctx):
    iltifatlar = [
        "Seninle tanışmak hayatımın en iyi şeyi!", "Ne kadar mükemmel bir insansın!",
        "Seni dinlerken ruhum huzur buluyor!", "Her söylediğin altın değerinde!",
        "Sen bir sanat eserisin!", "Dünya senin gibi birini hak ediyor!",
        "Varlığın bile etrafı aydınlatıyor!", "Ne kadar nazik ve kibar bir insansın!",
        "Seninle her anı yaşamak istiyorum!", "Gülüşün beni mutlu ediyor!"
    ]
    embed = discord.Embed(title="🌟 Yılankavi İltifat", description=random.choice(iltifatlar), color=discord.Color.magenta())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kupa(ctx):
    ulkeler = ["Fransa", "Brezilya", "Almanya", "Arjantin", "İngiltere", "İtalya", "İspanya", "Uruguay"]
    embed = discord.Embed(title="🏆 Dünya Kupası", description=f"Şampiyon: **{random.choice(ulkeler)}**", color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def ünlü(ctx):
    unluler = [
        {"isim": "Elon Musk", "meslek": "Girişimci"},
        {"isim": "Albert Einstein", "meslek": "Fizikçi"},
        {"isim": "Marie Curie", "meslek": "Kimyager"},
        {"isim": "Leonardo da Vinci", "meslek": "Ressam, Mucit"},
        {"isim": "Mustafa Kemal Atatürk", "meslek": "Devlet Adamı"},
        {"isim": "Cristiano Ronaldo", "meslek": "Futbolcu"},
        {"isim": "Serena Williams", "meslek": "Tenisçi"},
        {"isim": "Bill Gates", "meslek": "Yazılımcı"},
        {"isim": "Nikola Tesla", "meslek": "Mucit"},
        {"isim": "Barış Manço", "meslek": "Şarkıcı, Besteci"}
    ]
    secilen = random.choice(unluler)
    embed = discord.Embed(title="⭐ Rastgele Ünlü", description=f"**{secilen['isim']}** – {secilen['meslek']}", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kedi(ctx):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                data = await resp.json()
                url = data[0]['url']
        embed = discord.Embed(title="🐱 Kedi", color=discord.Color.orange())
        embed.set_image(url=url)
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ Kedi resmi getirilemedi.")

@bot.command()
async def köpek(ctx):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://dog.ceo/api/breeds/image/random") as resp:
                data = await resp.json()
                url = data['message']
        embed = discord.Embed(title="🐶 Köpek", color=discord.Color.brown())
        embed.set_image(url=url)
        await ctx.send(embed=embed)
    except:
        await ctx.send("❌ Köpek resmi getirilemedi.")

@bot.command()
async def sunucubilgi(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="👑 Sahip", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Üye", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Oluşturulma", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="💬 Kanal", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Rol", value=len(guild.roles), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def rolbilgi(ctx, rol: discord.Role):
    embed = discord.Embed(title=f"🎭 {rol.name}", color=rol.color)
    embed.add_field(name="ID", value=rol.id, inline=True)
    embed.add_field(name="Renk", value=str(rol.color), inline=True)
    embed.add_field(name="Üye Sayısı", value=len(rol.members), inline=True)
    embed.add_field(name="Oluşturulma", value=rol.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Yönetici mi?", value="Evet" if rol.permissions.administrator else "Hayır", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def öp(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 💋 {member.mention} öptü! 🥰", color=discord.Color.pink())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def tokat(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 👋 {member.mention} tokat attı! ***ŞAK***", color=discord.Color.red())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kartopu(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} ⛄ {member.mention} kartopu fırlattı! ❄️", color=discord.Color.light_grey())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def beşlik(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 🙏 {member.mention} beşlik çaktı!", color=discord.Color.green())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def sarıl(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 🤗 {member.mention} sarıldı!", color=discord.Color.magenta())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def tekme(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 🦵 {member.mention} tekme attı!", color=discord.Color.dark_red())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def adam_asmaca(ctx):
    kelimeler = ['python', 'discord', 'yazılım', 'bot', 'sunucu', 'klowinc']
    kelime = random.choice(kelimeler)
    tahmin = ['_'] * len(kelime)
    can = 5
    tahmin_edilen = []
    while can > 0 and '_' in tahmin:
        ascii_resim = adam_ascii(can)
        embed = discord.Embed(
            title="🔤 Adam Asmaca",
            description=f"```\n{ascii_resim}\n```\n**Kelime:** {' '.join(tahmin)}\n**Kalan Can:** {can}\n**Tahminlerin:** {', '.join(tahmin_edilen) if tahmin_edilen else 'Yok'}",
            color=discord.Color.blue()
        )
        embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
        def kontrol(m):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.content) == 1 and m.content.isalpha()
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=kontrol)
            harf = msg.content.lower()
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Zaman aşımı! Kelime: **{kelime}**")
            return
        if harf in tahmin_edilen:
            await ctx.send("Bu harfi zaten tahmin ettin!")
            continue
        tahmin_edilen.append(harf)
        if harf in kelime:
            for i, h in enumerate(kelime):
                if h == harf:
                    tahmin[i] = harf
            await ctx.send(f"✅ '{harf}' harfi kelimede var!")
        else:
            can -= 1
            await ctx.send(f"❌ '{harf}' harfi kelimede yok! Can: {can}")
    if '_' not in tahmin:
        embed = discord.Embed(title="🎉 Tebrikler!", description=f"Kelime: **{kelime}**", color=discord.Color.gold())
        embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="💀 Kaybettin!", description=f"Kelime: **{kelime}**", color=discord.Color.dark_red())
        embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

@bot.command()
async def sayı_tahmin(ctx):
    sayi = random.randint(1, 50)
    deneme = 0
    embed = discord.Embed(title="🎯 Sayı Tahmin", description="1-50 arası tahmin et! (10 hakkın)", color=discord.Color.green())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)
    while deneme < 10:
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit())
            tahmin = int(msg.content)
            deneme += 1
            if tahmin < sayi:
                await ctx.send(f"📈 Daha büyük! (Kalan: {10-deneme})")
            elif tahmin > sayi:
                await ctx.send(f"📉 Daha küçük! (Kalan: {10-deneme})")
            else:
                embed = discord.Embed(title="🎉 Tebrikler!", description=f"{deneme} denemede bildin! Sayı: **{sayi}**", color=discord.Color.gold())
                embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=embed)
                return
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Zaman aşımı! Sayı: **{sayi}**")
            return
    await ctx.send(f"💀 Kaybettin! Sayı: **{sayi}**")

@bot.command()
async def taş_kağıt_makas(ctx):
    secenekler = ['taş', 'kağıt', 'makas']
    bot_secim = random.choice(secenekler)
    embed = discord.Embed(title="✊ Taş, 📄 Kağıt, ✂️ Makas", description="Seçimini yaz (taş/kağıt/makas)", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for('message', timeout=30.0, check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in secenekler)
        kullanici_secim = msg.content.lower()
    except asyncio.TimeoutError:
        await ctx.send("⏰ Zaman aşımı!")
        return
    if kullanici_secim == bot_secim:
        sonuc = "🤝 Berabere!"
    elif (kullanici_secim == 'taş' and bot_secim == 'makas') or (kullanici_secim == 'kağıt' and bot_secim == 'taş') or (kullanici_secim == 'makas' and bot_secim == 'kağıt'):
        sonuc = "🎉 Kazandın!"
    else:
        sonuc = "💀 Kaybettin!"
    embed = discord.Embed(title="🎮 Sonuç", description=f"Sen: **{kullanici_secim}** | Bot: **{bot_secim}**\n{sonuc}", color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def efkarım(ctx):
    seviye = random.randint(0, 100)
    mesajlar = [
        "😊 Hiç efkarın yok, neşelisin!",
        "😐 Orta karar bir efkar var.",
        "😔 Biraz efkarlısın, bir şey mi oldu?",
        "😢 Çok efkarlısın, geçmiş olsun!",
        "💀 Efkardan geçilmiyor, aman dikkat!"
    ]
    embed = discord.Embed(title="📊 Efkar Seviyesi", description=f"{ctx.author.display_name} efkar seviyen: **{seviye}%**\n{mesajlar[seviye//25]}", color=discord.Color.dark_blue())
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kaç_cm(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    uzunluk = random.randint(3, 30)
    embed = discord.Embed(title="📏 Uzunluk Ölçer", description=f"**{member.display_name}**'in uzunluğu: **{uzunluk}cm** {':eggplant:' if uzunluk > 15 else '😅'}", color=discord.Color.purple())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def stresçarkı(ctx):
    carklar = ["🌀", "🔄", "🔁", "⏺️", "🔃"]
    embed = discord.Embed(title="🌀 Stres Çarkı", description=f"{ctx.author.mention} stres çarkını çevirdi! {random.choice(carklar)}", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def şanslı_renk(ctx):
    renkler = {
        "Kırmızı": "🔥 Ateş ve tutku!",
        "Mavi": "🌊 Huzur ve sakinlik!",
        "Yeşil": "🌿 Doğa ve şans!",
        "Sarı": "☀️ Enerji ve neşe!",
        "Mor": "👑 Lüks ve gizem!",
        "Turuncu": "🎃 Yaratıcılık ve coşku!",
        "Pembe": "🌸 Aşk ve romantizm!",
        "Siyah": "🖤 Güç ve zarafet!"
    }
    renk = random.choice(list(renkler.keys()))
    embed = discord.Embed(title="🎨 Şanslı Renk", description=f"{ctx.author.mention} şanslı rengin: **{renk}**\n{renkler[renk]}", color=discord.Color.gold())
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kader(ctx):
    yorumlar = [
        "🌠 Yıldızlar bugün çok parlak, şanslısın!",
        "🔮 Önünde büyük bir fırsat var, kaçırma!",
        "⚠️ Dikkatli ol, küçük bir aksilik olabilir.",
        "💫 Yeni bir başlangıç kapıda!",
        "🌟 Hayallerine bir adım daha yaklaştın.",
        "🌙 Bugün dinlenmeye ihtiyacın var."
    ]
    embed = discord.Embed(title="🔮 Kaderin", description=random.choice(yorumlar), color=discord.Color.dark_purple())
    embed.set_thumbnail(url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def çekiliş(ctx, *, ödül):
    embed = discord.Embed(title="🎉 ÇEKİLİŞ!", description=f"Ödül: **{ödül}**\nKatılmak için 🎉 emojisine tıkla!", color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    mesaj = await ctx.send(embed=embed)
    await mesaj.add_reaction("🎉")
    def kontrol(reaction, user):
        return str(reaction.emoji) == "🎉" and not user.bot
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=kontrol)
        embed2 = discord.Embed(title="📢 Çekiliş Başladı!", description=f"{reaction.count} kişi katıldı.", color=discord.Color.green())
        await ctx.send(embed=embed2)
    except asyncio.TimeoutError:
        await ctx.send("⏰ Çekiliş iptal, kimse katılmadı.")

@bot.command()
async def anket(ctx, *, soru):
    embed = discord.Embed(title="📊 ANKET", description=soru, color=discord.Color.blue())
    embed.set_footer(text=f"Anketi Başlatan: {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    mesaj = await ctx.send(embed=embed)
    await mesaj.add_reaction("✅")
    await mesaj.add_reaction("❌")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    embed = discord.Embed(description=f"👢 {member.name} sunucudan atıldı!", color=discord.Color.red())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    embed = discord.Embed(description=f"🔨 {member.name} banlandı!", color=discord.Color.dark_red())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def clear(ctx, miktar: int):
    if miktar < 1 or miktar > 1000:
        await ctx.send("❌ 1-1000 arası sayı girin.")
        return
    await ctx.channel.purge(limit=miktar+1)
    embed = discord.Embed(description=f"🗑️ {miktar} mesaj silindi.", color=discord.Color.orange())
    await ctx.send(embed=embed, delete_after=3)

# ==========================================
# YARDIM (Güncellendi)
# ==========================================

@bot.command()
async def yardım(ctx):
    embed = discord.Embed(
        title="📋 Komut Listesi",
        description="Botun tüm komutları (Normal + Self-Bot)",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🤖 SELF-BOT KOMUTLARI (Kendi hesabınla)",
        value="`!selfspam <sayı>` - Spam atar\n"
              "`!selfsil <sayı>` - Kendi mesajlarını siler\n"
              "`!selfmesajsil <sayı>` - Herkesin mesajını siler\n"
              "`!selfeveryone <mesaj>` - @everyone mesajı atar\n"
              "`!selfdm @kullanıcı <mesaj>` - DM gönderir\n"
              "`!selfkanalkopyala <kanal_id>` - Kanal kopyalar\n"
              "`!selfbottoken` - Token'ını gösterir",
        inline=False
    )
    embed.add_field(
        name="⚠️ YIKIM KOMUTLARI",
        value="`!sl`, `!sildur`, `!slhepsi`, `!spamwebhook`, `!spam`, `!spamyavas`, `!dur`\n"
              "`!rololuştur`, `!rolsil`, `!rolver`, `!rolat`, `!everyone`, `!dm`\n"
              "`!kanalkilit`, `!kanalaç`, `!kanaloluştur`, `!kanalsil`, `!kategorisil`\n"
              "`!tumrollersil`, `!sunucubosalt`, `!rastgeleat`, `!kanalpatlat`\n"
              "`!sunucuismi`, `!sunucuyedekle`, `!yedektenyukle`, `!rolyetkisi`\n"
              "`!servericon`, `!servername`, `!sıfırla`",
        inline=False
    )
    embed.add_field(
        name="😂 EĞLENCE",
        value="`!valdo`, `!gonu`, `!eternal`, `!klowinc`, `!doruk`, `!atam`\n"
              "`!furkandomalma`, `!furkanvideo`, `!zar`, `!yazitura`, `!şanslısayı`\n"
              "`!korkut`, `!aşkfalı`, `!tarih`, `!ping`, `!kullanıcıbilgi`\n"
              "`!ship`, `!eightball`, `!espri`, `!fbi`, `!avatar`, `!kompliman`\n"
              "`!hakaret`, `!yılankavi`, `!kupa`, `!ünlü`, `!kedi`, `!köpek`\n"
              "`!sunucubilgi`, `!rolbilgi`, `!öp`, `!tokat`, `!kartopu`, `!beşlik`\n"
              "`!sarıl`, `!tekme`, `!adam_asmaca`, `!sayı_tahmin`, `!taş_kağıt_makas`\n"
              "`!efkarım`, `!kaç_cm`, `!stresçarkı`, `!şanslı_renk`, `!kader`\n"
              "`!çekiliş`, `!anket`, `!kick`, `!ban`, `!clear`",
        inline=False
    )
    embed.set_footer(text="⚠️ Self-bot Discord ToS'a aykırıdır! Risk sana ait.")
    await ctx.send(embed=embed)

# ==========================================
# BAŞLATMA
# ==========================================

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        # self_bot=True ile başlatıyoruz
        bot.run(token, bot=False)  # bot=False = self-bot modu
    else:
        print("❌ DISCORD_TOKEN ayarlanmamış!")