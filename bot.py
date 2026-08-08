import discord
from discord.ext import commands
import asyncio
import os
import random
import aiohttp
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from flask import Flask
from threading import Thread

# --- Flask Web Sunucusu ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot aktif!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# --- Discord Bot Ayarları ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- Global Değişkenler ---
spam_aktif = False
silme_aktif = False

# --- Bot Olayları ---
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!yardım"))
    print(f'✅ Bot hazır: {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Yetkin yetmiyor, otur ağla.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Eksik argüman. Doğru kullanım: `{ctx.command.name} {ctx.command.signature}`")
    else:
        print(f"Hata: {error}")
        await ctx.send(f"❌ Hata: {str(error)[:100]}")

# --- Yardımcı Fonksiyon: Adam Asmaca ASCII Art ---
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

# --- Yardımcı Fonksiyon: Ship için avatar birleştir ---
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

# ========================
# YIKIM KOMUTLARI (Admin)
# ========================

# --- Yavaş silme (0.5 saniye arayla) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def sl(ctx):
    global silme_aktif
    if silme_aktif:
        await ctx.send("⚠️ Zaten silme işlemi aktif.")
        return
    silme_aktif = True
    await ctx.send("🗑️ Tüm kanallar 0.5 saniye arayla siliniyor... (!sildur ile durdur)")
    for kanal in ctx.guild.channels:
        if not silme_aktif:
            break
        try:
            await kanal.delete()
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Silme hatası: {e}")
    silme_aktif = False
    await ctx.send("✅ Kanallar silme işlemi tamamlandı veya durduruldu.")

# --- Durdur ---
@bot.command()
@commands.has_permissions(administrator=True)
async def sildur(ctx):
    global silme_aktif
    silme_aktif = False
    await ctx.send("🛑 Kanal silme durduruldu.")

# --- TEK SEFERDE TÜM KANALLARI SİL (YENİ) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def slhepsi(ctx):
    """Tüm kanalları tek seferde silmeye çalışır (riskli!)"""
    await ctx.send("💥 Tüm kanallar tek seferde siliniyor...")
    kanallar = ctx.guild.channels
    basarili = 0
    basarisiz = 0
    
    for kanal in kanallar:
        try:
            await kanal.delete()
            basarili += 1
        except Exception as e:
            basarisiz += 1
            print(f"Silinemedi: {kanal.name} - {e}")
    
    await ctx.send(f"✅ **{basarili}** kanal silindi.\n❌ **{basarisiz}** kanal silinemedi.")

# --- Hızlı spam (aynı anda tüm kanallara, 0.7 saniye bekle) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def spam(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("⚠️ Zaten spam aktif.")
        return
    spam_aktif = True
    await ctx.send("🔊 Hızlı spam başladı! Tüm kanallara aynı anda mesaj gidiyor. (!dur ile durdur)")
    while spam_aktif:
        tasks = []
        for kanal in ctx.guild.text_channels:
            tasks.append(kanal.send("KLOWINC BİR UGRADI! @everyone"))
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.7)
    await ctx.send("✅ Spam durduruldu.")

# --- Yavaş spam (tek tek) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def spamyavas(ctx):
    global spam_aktif
    if spam_aktif:
        await ctx.send("⚠️ Zaten spam aktif.")
        return
    spam_aktif = True
    await ctx.send("🐢 Yavaş spam başladı! Kanallar tek tek mesaj alacak. (!dur ile durdur)")
    while spam_aktif:
        for kanal in ctx.guild.text_channels:
            if not spam_aktif:
                break
            try:
                await kanal.send("KLOWINC BİR UGRADI! @everyone")
            except Exception as e:
                print(f"Spam hatası: {e}")
        await asyncio.sleep(0.5)
    await ctx.send("✅ Spam durduruldu.")

# --- Spam durdur ---
@bot.command()
@commands.has_permissions(administrator=True)
async def dur(ctx):
    global spam_aktif
    spam_aktif = False
    await ctx.send("🛑 Spam durduruldu.")

# --- Diğer Yıkım Komutları ---
@bot.command()
@commands.has_permissions(manage_roles=True)
async def roluştur(ctx, *, isim):
    try:
        rol = await ctx.guild.create_role(name=isim)
        embed = discord.Embed(description=f"✅ `{rol.name}` adlı rol oluşturuldu!", color=discord.Color.green())
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Rol oluşturulamadı: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def rolsil(ctx, rol: discord.Role):
    try:
        await rol.delete()
        embed = discord.Embed(description=f"✅ `{rol.name}` adlı rol silindi!", color=discord.Color.red())
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Rol silinemedi: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def everyone(ctx, *, mesaj):
    await ctx.send(f"@everyone {mesaj}")

@bot.command()
@commands.has_permissions(administrator=True)
async def kanalkilit(ctx):
    for kanal in ctx.guild.text_channels:
        try:
            await kanal.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    embed = discord.Embed(description="🔒 Tüm kanallar kilitlendi!", color=discord.Color.dark_red())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def kanalaç(ctx):
    for kanal in ctx.guild.text_channels:
        try:
            await kanal.set_permissions(ctx.guild.default_role, send_messages=None)
        except:
            pass
    embed = discord.Embed(description="🔓 Tüm kanalların kilidi açıldı!", color=discord.Color.green())
    await ctx.send(embed=embed)

# ========================
# ESKİ EĞLENCE (Embed)
# ========================

@bot.command()
async def valdo(ctx):
    embed = discord.Embed(description="YARRAMM VALDO BU KIM AMK", color=discord.Color.red())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def gonu(ctx):
    embed = discord.Embed(description="2 GUNDE 48 CK ATAN ADAM", color=discord.Color.green())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def eternal(ctx):
    embed = discord.Embed(description="FURKANIN NAMIDEGER BABASI", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def klowinc(ctx):
    embed = discord.Embed(description="BU ADAMIN TASSAKLARINA BETON YETMEZ", color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def doruk(ctx):
    embed = discord.Embed(description="ARİEL BABAAAA", color=discord.Color.purple())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# --- MEDYA ---
@bot.command()
async def atam(ctx):
    try:
        await ctx.send(file=discord.File('ataturk.jpg'))
    except FileNotFoundError:
        await ctx.send("❌ ataturk.jpg bulunamadı.")

@bot.command()
async def furkandomalma(ctx):
    try:
        await ctx.send(file=discord.File('furkandomalma.jpg'))
    except FileNotFoundError:
        await ctx.send("❌ furkandomalma.jpg bulunamadı.")

@bot.command()
async def furkanvideo(ctx):
    try:
        await ctx.send(file=discord.File('furkan.mp4'))
    except FileNotFoundError:
        await ctx.send("❌ furkan.mp4 bulunamadı.")

# ========================
# GÖRSEL EĞLENCE KOMUTLARI
# ========================

@bot.command()
async def zar(ctx):
    sonuc = random.randint(1, 6)
    zar_emoji = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    embed = discord.Embed(title="🎲 Zar Atıldı", description=f"**{sonuc}** {zar_emoji[sonuc-1]}", color=discord.Color.blue())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def yazitura(ctx):
    sonuc = random.choice(["Yazı", "Tura"])
    embed = discord.Embed(title="🪙 Yazı Tura", description=f"**{sonuc}** geldi!", color=discord.Color.green())
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
    korkular = [
        "👻 Arkanda biri var!",
        "💀 Gece yarısı kapını çalacaklar...",
        "🔪 Sessiz ol, seni izliyorlar!",
        "🕷️ Yatağının altında bir şey var...",
        "🧟 Zombi saldırısı başladı!",
        "👽 Uzaylılar geldi, kaç!"
    ]
    embed = discord.Embed(title="👻 KORKU", description=random.choice(korkular), color=discord.Color.dark_red())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def aşkfalı(ctx, *, isim=None):
    if isim is None:
        isim = ctx.author.display_name
    uyeler = [uye for uye in ctx.guild.members if not uye.bot and uye != ctx.author]
    if uyeler:
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
        embed.set_footer(text=f"{ctx.author.display_name} için fal", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Yeterli üye yok.")

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

# --- YENİ EĞLENCE KOMUTLARI ---
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
    embed = discord.Embed(title="🏆 Dünya Kupası Şampiyonu", description=f"Rastgele şampiyon: **{random.choice(ulkeler)}**", color=discord.Color.gold())
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

# ========================
# MEDYA API'Lİ KOMUTLAR
# ========================

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

# --- Sunucu Bilgi ---
@bot.command()
async def sunucubilgi(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"📊 {guild.name} Sunucu Bilgisi", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="👑 Sahip", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Üye Sayısı", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Oluşturulma", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="💬 Kanal Sayısı", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Rol Sayısı", value=len(guild.roles), inline=True)
    embed.add_field(name="🌍 Bölge", value=str(guild.region) if guild.region else "Belirtilmemiş", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def rolbilgi(ctx, rol: discord.Role):
    embed = discord.Embed(title=f"🎭 {rol.name} Rol Bilgisi", color=rol.color)
    embed.add_field(name="ID", value=rol.id, inline=True)
    embed.add_field(name="Renk", value=str(rol.color), inline=True)
    embed.add_field(name="Üye Sayısı", value=len(rol.members), inline=True)
    embed.add_field(name="Oluşturulma", value=rol.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Bot mu?", value="Evet" if rol.is_bot_managed() else "Hayır", inline=True)
    embed.add_field(name="Yönetici mi?", value="Evet" if rol.permissions.administrator else "Hayır", inline=True)
    await ctx.send(embed=embed)

# ========================
# SOSYAL KOMUTLAR
# ========================

@bot.command()
async def öp(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 💋 {member.mention} adlı kişiyi öptü! 🥰", color=discord.Color.pink())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def tokat(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 👋 {member.mention} adlı kişiye bir tokat attı! ***ŞAK***", color=discord.Color.red())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def kartopu(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} ⛄ {member.mention} adlı kişiye kartopu fırlattı! ❄️", color=discord.Color.light_grey())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def beşlik(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 🙏 {member.mention} ile beşlik çaktı! ÇAKK", color=discord.Color.green())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def sarıl(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 🤗 {member.mention} adlı kişiye sarıldı! 🤗", color=discord.Color.magenta())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def tekme(ctx, member: discord.Member):
    embed = discord.Embed(description=f"{ctx.author.mention} 🦵 {member.mention} adlı kişiye bir tekme attı! ***PAT***", color=discord.Color.dark_red())
    embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# ========================
# OYUNLAR
# ========================

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
        embed = discord.Embed(title="🎉 Tebrikler!", description=f"Kelimeyi buldun: **{kelime}**", color=discord.Color.gold())
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
    embed = discord.Embed(title="🎯 Sayı Tahmin", description="1 ile 50 arasında bir sayı tahmin et! (10 deneme hakkın)", color=discord.Color.green())
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
    elif (kullanici_secim == 'taş' and bot_secim == 'makas') or \
         (kullanici_secim == 'kağıt' and bot_secim == 'taş') or \
         (kullanici_secim == 'makas' and bot_secim == 'kağıt'):
        sonuc = "🎉 Kazandın!"
    else:
        sonuc = "💀 Kaybettin!"
    
    embed = discord.Embed(title="🎮 Sonuç", description=f"Sen: **{kullanici_secim}** | Bot: **{bot_secim}**\n{sonuc}", color=discord.Color.gold())
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# ========================
# KOMİK KOMUTLAR
# ========================

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

# ========================
# YÖNETİM
# ========================

@bot.command()
@commands.has_permissions(administrator=True)
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
    embed = discord.Embed(
        title="📊 ANKET",
        description=soru,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Anketi Başlatan: {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    mesaj = await ctx.send(embed=embed)
    await mesaj.add_reaction("✅")
    await mesaj.add_reaction("❌")

# ========================
# MODERASYON
# ========================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    embed = discord.Embed(description=f"👢 {member.name} sunucudan atıldı!", color=discord.Color.red())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    embed = discord.Embed(description=f"🔨 {member.name} banlandı!", color=discord.Color.dark_red())
    embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, miktar: int):
    if miktar < 1 or miktar > 1000:
        await ctx.send("❌ 1-1000 arası sayı girin.")
        return
    await ctx.channel.purge(limit=miktar+1)
    embed = discord.Embed(description=f"🗑️ {miktar} mesaj silindi.", color=discord.Color.orange())
    await ctx.send(embed=embed, delete_after=3)

# ========================
# YARDIM (Güncellendi)
# ========================

@bot.command()
async def yardım(ctx):
    embed = discord.Embed(
        title="📋 Komut Listesi",
        description="Botun tüm komutları (görsel zengin!)",
        color=discord.Color.blue()
    )
    embed.add_field(name="⚠️ Yıkım (Admin)", value="`!sl` (yavaş sil), `!slhepsi` (tek seferde sil)\n`!sildur` (durdur)\n`!spam` (hızlı), `!spamyavas` (yavaş), `!dur`\n`!rololuştur <isim>`, `!rolsil <rol>`\n`!everyone <mesaj>`, `!kanalkilit`, `!kanalaç`", inline=False)
    embed.add_field(name="😂 Eski Eğlence", value="`!valdo`, `!gonu`, `!eternal`, `!klowinc`, `!doruk`", inline=False)
    embed.add_field(name="🎲 Klasik Eğlence", value="`!zar`, `!yazitura`, `!şanslısayı`, `!korkut`, `!aşkfalı`", inline=False)
    embed.add_field(name="📅 Bilgi", value="`!tarih`, `!ping`, `!kullanıcıbilgi`, `!sunucubilgi`, `!rolbilgi <rol>`", inline=False)
    embed.add_field(name="💞 Romantik", value="`!ship @kisi1 @kisi2`, `!eightball <soru>`, `!espri`", inline=False)
    embed.add_field(name="🖼️ Medya", value="`!atam`, `!furkandomalma`, `!furkanvideo`, `!fbi`, `!avatar @kisi`, `!kedi`, `!köpek`", inline=False)
    embed.add_field(name="👋 Sosyal", value="`!öp`, `!tokat`, `!kartopu`, `!beşlik`, `!sarıl`, `!tekme`", inline=False)
    embed.add_field(name="🎮 Oyunlar", value="`!adam_asmaca`, `!sayı_tahmin`, `!taş_kağıt_makas`", inline=False)
    embed.add_field(name="🤣 Komik & İlginç", value="`!efkarım`, `!kaç_cm`, `!stresçarkı`, `!şanslı_renk`, `!kader`, `!kompliman`, `!hakaret`, `!yılankavi`, `!kupa`, `!ünlü`", inline=False)
    embed.add_field(name="📊 Yönetim", value="`!çekiliş <ödül>`, `!anket <soru>`", inline=False)
    embed.add_field(name="🔨 Moderasyon", value="`!kick @kisi`, `!ban @kisi`, `!clear <sayı>`", inline=False)
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