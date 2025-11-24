import sqlite3
import random
from datetime import datetime, timedelta

# --- 1. AYARLAR ---
random.seed(42)

# --- 2. KATALOG ---
CIHAZ_KATALOGU = {
    "Bosch": {
        "Buzdolabı": {"watt": 150, "frekans": (1, 1), "sure_dk": 1440},
        "Fırın": {"watt": 2200, "frekans": (0, 2), "sure_dk": 60}
    },
    "Samsung": {
        "TV": {"watt": 120, "frekans": (1, 3), "sure_dk": 120},
        "Klima": {"watt": 1500, "frekans": (0, 3), "sure_dk": 60}
    },
    "Arçelik": {
        "Ütü": {"watt": 2400, "frekans": (0, 2), "sure_dk": 45},
        "Çay Makinası": {"watt": 1800, "frekans": (2, 5), "sure_dk": 20}
    },
    "Dyson": {
        "Süpürge": {"watt": 600, "frekans": (0, 1), "sure_dk": 40}
    }
}


# --- 3. SINIF TANIMLARI ---

class Sirket:
    def __init__(self, id, isim):
        self.id = id
        self.isim = isim


class Tarife:
    def __init__(self, sirket_id, t1_gunduz, t2_puant, t3_gece):
        self.sirket_id = sirket_id
        # [Zaman Aralığı, Fiyat]
        self.t1_gunduz = t1_gunduz  # 06-17
        self.t2_puant = t2_puant  # 17-22 (En pahalı)
        self.t3_gece = t3_gece  # 22-06 (En ucuz)

    def saat_fiyati_getir(self, saat):
        """Verilen saatin hangi tarife dilimine girdiğini ve fiyatını döndürür."""
        if 6 <= saat < 17:
            return self.t1_gunduz[1]
        elif 17 <= saat < 22:
            return self.t2_puant[1]
        else:
            return self.t3_gece[1]


class EvAleti:
    def __init__(self, id, tur, marka, ozellikler, ev_id):
        self.id = id
        self.tur = tur
        self.marka = marka
        self.watt = ozellikler['watt']
        self.frekans_min, self.frekans_max = ozellikler['frekans']
        self.sure_dk = ozellikler['sure_dk']
        self.ev_id = ev_id
        self.gunluk_loglar = {}
        self.toplam_tuketim_wh = 0

    def aylik_simulasyon_yap(self, yil, ay):
        gun_sayisi = 30
        baslangic_tarihi = datetime(yil, ay, 1)

        for i in range(gun_sayisi):
            gecerli_gun = baslangic_tarihi + timedelta(days=i)
            tarih_str = gecerli_gun.strftime("%d.%m.%Y")
            calisma_sayisi = random.randint(self.frekans_min, self.frekans_max)

            if calisma_sayisi > 0 and tarih_str not in self.gunluk_loglar:
                self.gunluk_loglar[tarih_str] = []

            # Buzdolabı gibi sürekli çalışan cihazlar
            if self.sure_dk == 1440 and calisma_sayisi > 0:
                self.gunluk_loglar[tarih_str].append("00.00-23.59")
                self.toplam_tuketim_wh += (self.watt * 24)
                continue

            kullanilan_saatler = set()
            for _ in range(calisma_sayisi):
                baslangic_saati = random.randint(8, 23)  # Gece kullanımını artırmak için aralığı genişlettim
                # Saat 24'ü geçerse basitlik adına 23 yapıyoruz (Simülasyon kısıtı)
                if baslangic_saati > 23: baslangic_saati = 23

                if baslangic_saati in kullanilan_saatler: continue
                kullanilan_saatler.add(baslangic_saati)

                bitis_dakika_toplam = (baslangic_saati * 60) + self.sure_dk
                bitis_saati = int(bitis_dakika_toplam // 60)
                bitis_dk_kalan = int(bitis_dakika_toplam % 60)

                # Gün aşımı kontrolü (Basit tutmak için aynı günde bitiriyoruz)
                if bitis_saati >= 24:
                    bitis_saati = 23
                    bitis_dk_kalan = 59

                zaman_araligi = f"{baslangic_saati:02d}.00-{bitis_saati:02d}.{bitis_dk_kalan:02d}"
                self.gunluk_loglar[tarih_str].append(zaman_araligi)
                self.toplam_tuketim_wh += (self.watt * (self.sure_dk / 60))

            if tarih_str in self.gunluk_loglar:
                self.gunluk_loglar[tarih_str].sort()


class Ev:
    def __init__(self, id, adres, user_id):
        self.id = id
        self.adres = adres
        self.user_id = user_id
        self.ev_aletleri = []
        self.aylik_toplam_tuketim = 0

    def alet_ekle(self, alet):
        self.ev_aletleri.append(alet)

    def hesapla(self):
        self.aylik_toplam_tuketim = sum(alet.toplam_tuketim_wh for alet in self.ev_aletleri)


class User:
    def __init__(self, id, isim, soyisim, sirket_id, score=0):
        self.id = id
        self.isim = isim
        self.soyisim = soyisim
        self.sirket_id = sirket_id
        self.score = score
        self.evler = []

    def ev_ekle(self, ev):
        self.evler.append(ev)


# --- 4. DATA OLUŞTURMA VE HESAPLAMA ---

def sirket_datalari_olustur():
    """Şirket ve Tarife datalarını oluşturur."""
    sirketler = []
    tarifeler = []  # List of Tarife objects

    sirket_isimleri = ["Gediz Elektrik", "Enerjisa", "CK Enerji"]

    for i, isim in enumerate(sirket_isimleri, 1):
        sirket = Sirket(i, isim)
        sirketler.append(sirket)

        # Fiyatlandırma
        base_price = 2.0 + (i * 0.1)
        t1 = ["06:00-17:00", round(base_price, 2)]  # Gündüz
        t2 = ["17:00-22:00", round(base_price * 1.6, 2)]  # Puant (Pahalı)
        t3 = ["22:00-06:00", round(base_price * 0.5, 2)]  # Gece (Ucuz)

        tarife = Tarife(sirket.id, t1, t2, t3)
        tarifeler.append(tarife)

    return sirketler, tarifeler


def kullanici_verileri_olustur(mevcut_sirketler):
    users = []
    kullanici_listesi = [
        (1, "Ahmet", "Tasarrufçu"),
        (2, "Ayşe", "Normal"),
        (3, "Mehmet", "Savurgan")
    ]
    ev_adresleri = ["Kadıköy", "Beşiktaş", "Çankaya", "Bornova", "Nilüfer"]
    ev_sahiplikleri = [0, 0, 1, 1, 2]
    sirket_ids = [s.id for s in mevcut_sirketler]

    user_objects = []
    for id, ad, soyad in kullanici_listesi:
        rnd_sirket_id = random.choice(sirket_ids)
        # Score başlangıçta 0, hesaplamayla güncellenecek
        user_objects.append(User(id, ad, soyad, rnd_sirket_id, 0))

    for i, adres in enumerate(ev_adresleri):
        sahip_idx = ev_sahiplikleri[i]
        user = user_objects[sahip_idx]
        ev = Ev(100 + i, adres, user.id)

        # Mehmet (Savurgan) için daha fazla klima/fırın ekleyelim
        if user.isim == "Mehmet":
            alet_sayisi = 6
        else:
            alet_sayisi = random.randint(3, 5)

        for k in range(alet_sayisi):
            marka = random.choice(list(CIHAZ_KATALOGU.keys()))
            tur = random.choice(list(CIHAZ_KATALOGU[marka].keys()))
            ozellikler = CIHAZ_KATALOGU[marka][tur]

            alet = EvAleti(int(f"{ev.id}{k}"), tur, marka, ozellikler, ev.id)

            # --- DAVRANIŞ MANİPÜLASYONU (TEST İÇİN) ---
            # Simülasyon parametrelerini manipüle ediyoruz ki skor farkı oluşsun
            if user.isim == "Ahmet":
                # Gece çalışsın (Ucuz)
                alet.frekans_min, alet.frekans_max = (1, 2)
                # Simülasyon fonksiyonu normalde 8-23 arası atıyor,
                # bunu hesaplama fonksiyonunda manipüle etmek yerine
                # simülasyon sonrası logları manuel kaydırabilirdik ama
                # şimdilik rastgelelik içinde Ahmet şanslı olsun diye
                # manuel müdahale etmiyoruz, rastgele sonuca güveniyoruz.

            alet.aylik_simulasyon_yap(2025, 11)
            ev.alet_ekle(alet)

        ev.hesapla()
        user.ev_ekle(ev)

    return user_objects


def kullanici_skorlarini_hesapla(users, tarifeler):
    """
    Her kullanıcının tüketim saatlerine bakarak maliyet hesabı yapar
    ve 0-100 arasında bir verimlilik puanı atar.
    """
    # Tarife listesini hızlı erişim için dict'e çevir
    tarife_map = {t.sirket_id: t for t in tarifeler}

    print("\n📊 SKOR HESAPLAMA BAŞLADI...")

    for user in users:
        tarife = tarife_map.get(user.sirket_id)
        if not tarife: continue

        toplam_maliyet_tl = 0
        toplam_enerji_wh = 0

        # Şirketin birim fiyat sınırları
        max_fiyat = tarife.t2_puant[1]  # En pahalı
        min_fiyat = tarife.t3_gece[1]  # En ucuz

        for ev in user.evler:
            for alet in ev.ev_aletleri:
                for tarih, logs in alet.gunluk_loglar.items():
                    for log in logs:
                        # Log format: "12.00-13.30"
                        baslangic_str, bitis_str = log.split('-')
                        baslangic_saati = int(baslangic_str.split('.')[0])

                        # Tüketim miktarı (Wh)
                        if alet.sure_dk == 1440:  # 24 saatlik cihaz
                            tuketim = alet.watt * 24
                            # 24 saatlik cihaz ortalama bir fiyattan hesaplanır
                            # (11s Gündüz + 5s Puant + 8s Gece) / 24
                            avg_24h_fiyat = ((11 * tarife.t1_gunduz[1]) +
                                             (5 * tarife.t2_puant[1]) +
                                             (8 * tarife.t3_gece[1])) / 24
                            birim_fiyat = avg_24h_fiyat
                        else:
                            tuketim = alet.watt * (alet.sure_dk / 60)
                            # Çalıştığı saatin tarifesini al
                            birim_fiyat = tarife.saat_fiyati_getir(baslangic_saati)

                        toplam_enerji_wh += tuketim
                        toplam_maliyet_tl += (tuketim / 1000) * birim_fiyat

        if toplam_enerji_wh == 0:
            user.score = 50  # Tüketim yoksa nötr
            continue

        # Kullanıcının Ortalama Birim Maliyeti (TL/kWh)
        user_avg_maliyet = toplam_maliyet_tl / (toplam_enerji_wh / 1000)

        # NORMALİZASYON: (Max - UserAvg) / (Max - Min) * 100
        # Eğer en ucuza kullandıysa (UserAvg = Min) -> (Max-Min)/(Max-Min) = 1 -> 100 Puan
        # Eğer en pahalıya kullandıysa (UserAvg = Max) -> 0/Fark = 0 Puan

        fiyat_araligi = max_fiyat - min_fiyat
        if fiyat_araligi == 0:
            score = 100
        else:
            score = ((max_fiyat - user_avg_maliyet) / fiyat_araligi) * 100

        # Sınırlandırma
        score = max(0, min(100, score))
        user.score = round(score, 2)

        print(
            f"   👤 {user.isim}: Ort.Maliyet: {user_avg_maliyet:.2f} TL/kWh (Min:{min_fiyat}, Max:{max_fiyat}) -> SKOR: {user.score}")


# --- 5. VERİTABANI İŞLEMLERİ ---

def veritabani_kur():
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS Sirketler (id INTEGER PRIMARY KEY, isim TEXT)")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Users
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       isim
                       TEXT,
                       soyisim
                       TEXT,
                       sirket_id
                       INTEGER,
                       score
                       REAL,
                       FOREIGN
                       KEY
                   (
                       sirket_id
                   ) REFERENCES Sirketler
                   (
                       id
                   )
                       )""")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Evler
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       adres
                       TEXT,
                       user_id
                       INTEGER,
                       toplam_tuketim_kwh
                       REAL,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES Users
                   (
                       id
                   )
                       )""")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Aletler
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY,
                       tur
                       TEXT,
                       marka
                       TEXT,
                       watt
                       INTEGER,
                       ev_id
                       INTEGER,
                       FOREIGN
                       KEY
                   (
                       ev_id
                   ) REFERENCES Evler
                   (
                       id
                   )
                       )""")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS TuketimLoglari
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       alet_id
                       INTEGER,
                       tarih
                       TEXT,
                       baslangic_saati
                       TEXT,
                       bitis_saati
                       TEXT,
                       tuketim_wh
                       REAL,
                       FOREIGN
                       KEY
                   (
                       alet_id
                   ) REFERENCES Aletler
                   (
                       id
                   )
                       )""")
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS Tarifeler
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       sirket_id
                       INTEGER,
                       t1_aralik
                       TEXT,
                       t1_fiyat
                       REAL,
                       t2_aralik
                       TEXT,
                       t2_fiyat
                       REAL,
                       t3_aralik
                       TEXT,
                       t3_fiyat
                       REAL,
                       FOREIGN
                       KEY
                   (
                       sirket_id
                   ) REFERENCES Sirketler
                   (
                       id
                   )
                       )""")
    conn.commit()
    conn.close()


def verileri_kaydet(users, sirketler, tarifeler):
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()

    for s in sirketler:
        cursor.execute("INSERT OR REPLACE INTO Sirketler VALUES (?, ?)", (s.id, s.isim))

    for t in tarifeler:
        cursor.execute("""INSERT OR REPLACE INTO Tarifeler 
            (sirket_id, t1_aralik, t1_fiyat, t2_aralik, t2_fiyat, t3_aralik, t3_fiyat) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (t.sirket_id, t.t1_gunduz[0], t.t1_gunduz[1], t.t2_puant[0], t.t2_puant[1], t.t3_gece[0],
                        t.t3_gece[1]))

    for u in users:
        cursor.execute("INSERT OR REPLACE INTO Users VALUES (?, ?, ?, ?, ?)",
                       (u.id, u.isim, u.soyisim, u.sirket_id, u.score))
        for ev in u.evler:
            cursor.execute("INSERT OR REPLACE INTO Evler VALUES (?, ?, ?, ?)",
                           (ev.id, ev.adres, u.id, ev.aylik_toplam_tuketim / 1000))
            for alet in ev.ev_aletleri:
                cursor.execute("INSERT OR REPLACE INTO Aletler VALUES (?, ?, ?, ?, ?)",
                               (alet.id, alet.tur, alet.marka, alet.watt, ev.id))
                for tarih, logs in alet.gunluk_loglar.items():
                    for aralik in logs:
                        bas, bit = aralik.split('-')
                        if alet.sure_dk == 1440:
                            tuk = alet.watt * 24
                        else:
                            tuk = alet.watt * (alet.sure_dk / 60)
                        cursor.execute(
                            "INSERT INTO TuketimLoglari (alet_id, tarih, baslangic_saati, bitis_saati, tuketim_wh) VALUES (?, ?, ?, ?, ?)",
                            (alet.id, tarih, bas, bit, tuk))
    conn.commit()
    conn.close()
    print("✅ Tüm veriler kaydedildi.")


def kontrol_sorgusu():
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()
    print("\n--- 🏆 KULLANICI SKOR TABLOSU ---")
    rows = cursor.execute("SELECT isim, score FROM Users ORDER BY score DESC").fetchall()
    for r in rows:
        print(f"⭐ {r[0]}: {r[1]} Puan")
    conn.close()


# --- MAIN ---
if __name__ == "__main__":
    veritabani_kur()
    sirketler, tarifeler = sirket_datalari_olustur()
    users = kullanici_verileri_olustur(sirketler)

    # Yeni eklenen fonksiyon: Skorları hesapla ve user objelerine yaz
    kullanici_skorlarini_hesapla(users, tarifeler)

    verileri_kaydet(users, sirketler, tarifeler)
    kontrol_sorgusu()

