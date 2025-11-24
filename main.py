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
        self.t1_gunduz = t1_gunduz
        self.t2_puant = t2_puant
        self.t3_gece = t3_gece

    def saat_fiyati_getir(self, saat):
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
            if self.sure_dk == 1440 and calisma_sayisi > 0:
                self.gunluk_loglar[tarih_str].append("00.00-23.59")
                self.toplam_tuketim_wh += (self.watt * 24)
                continue
            kullanilan_saatler = set()
            for _ in range(calisma_sayisi):
                baslangic_saati = random.randint(8, 23)
                if baslangic_saati > 23: baslangic_saati = 23
                if baslangic_saati in kullanilan_saatler: continue
                kullanilan_saatler.add(baslangic_saati)
                bitis_dakika_toplam = (baslangic_saati * 60) + self.sure_dk
                bitis_saati = int(bitis_dakika_toplam // 60)
                bitis_dk_kalan = int(bitis_dakika_toplam % 60)
                if bitis_saati >= 24:
                    bitis_saati = 23;
                    bitis_dk_kalan = 59
                zaman_araligi = f"{baslangic_saati:02d}.00-{bitis_saati:02d}.{bitis_dk_kalan:02d}"
                self.gunluk_loglar[tarih_str].append(zaman_araligi)
                self.toplam_tuketim_wh += (self.watt * (self.sure_dk / 60))
            if tarih_str in self.gunluk_loglar: self.gunluk_loglar[tarih_str].sort()


class Ev:
    def __init__(self, id, adres, user_id):
        self.id = id
        self.adres = adres
        self.user_id = user_id
        self.ev_aletleri = []
        self.aylik_toplam_tuketim = 0
        # --- YENİ ÖZELLİK: Hedef Sıcaklık ---
        # Kullanıcının evi kaç derecede tutmak istediği (20 ile 26 arası rastgele)
        self.hedef_sicaklik = random.randint(20, 26)

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

    def ev_ekle(self, ev): self.evler.append(ev)


# --- 4. DATA OLUŞTURMA ---
def sirket_datalari_olustur():
    sirketler = []
    tarifeler = []
    sirket_isimleri = ["Gediz Elektrik", "Enerjisa", "CK Enerji"]
    for i, isim in enumerate(sirket_isimleri, 1):
        sirket = Sirket(i, isim)
        sirketler.append(sirket)
        base_price = 2.0 + (i * 0.1)
        tarife = Tarife(sirket.id, ["06-17", round(base_price, 2)], ["17-22", round(base_price * 1.6, 2)],
                        ["22-06", round(base_price * 0.5, 2)])
        tarifeler.append(tarife)
    return sirketler, tarifeler


def kullanici_verileri_olustur(mevcut_sirketler):
    users = []
    kullanici_listesi = [(1, "Ahmet", "Tasarrufçu"), (2, "Ayşe", "Normal"), (3, "Mehmet", "Savurgan")]
    ev_adresleri = ["Kadıköy", "Beşiktaş", "Çankaya", "Bornova", "Nilüfer"]
    ev_sahiplikleri = [0, 0, 1, 1, 2]
    sirket_ids = [s.id for s in mevcut_sirketler]
    user_objects = []
    for id, ad, soyad in kullanici_listesi:
        user_objects.append(User(id, ad, soyad, random.choice(sirket_ids), 0))
    for i, adres in enumerate(ev_adresleri):
        sahip_idx = ev_sahiplikleri[i]
        user = user_objects[sahip_idx]
        ev = Ev(100 + i, adres, user.id)
        alet_sayisi = 6 if user.isim == "Mehmet" else random.randint(3, 5)
        for k in range(alet_sayisi):
            marka = random.choice(list(CIHAZ_KATALOGU.keys()))
            tur = random.choice(list(CIHAZ_KATALOGU[marka].keys()))
            ozellikler = CIHAZ_KATALOGU[marka][tur]
            alet = EvAleti(int(f"{ev.id}{k}"), tur, marka, ozellikler, ev.id)
            if user.isim == "Ahmet": alet.frekans_min, alet.frekans_max = (1, 2)
            alet.aylik_simulasyon_yap(2025, 11)
            ev.alet_ekle(alet)
        ev.hesapla()
        user.ev_ekle(ev)
    return user_objects


def kullanici_skorlarini_hesapla(users, tarifeler):
    tarife_map = {t.sirket_id: t for t in tarifeler}
    print("\n📊 SKOR HESAPLAMA BAŞLADI...")
    for user in users:
        tarife = tarife_map.get(user.sirket_id)
        if not tarife: continue
        toplam_maliyet_tl = 0;
        toplam_enerji_wh = 0
        max_fiyat = tarife.t2_puant[1];
        min_fiyat = tarife.t3_gece[1]
        for ev in user.evler:
            for alet in ev.ev_aletleri:
                for logs in alet.gunluk_loglar.values():
                    for log in logs:
                        bas, _ = log.split('-')
                        baslangic_saati = int(bas.split('.')[0])
                        if alet.sure_dk == 1440:
                            tuketim = alet.watt * 24
                            avg_24h_fiyat = ((11 * tarife.t1_gunduz[1]) + (5 * tarife.t2_puant[1]) + (
                                        8 * tarife.t3_gece[1])) / 24
                            birim_fiyat = avg_24h_fiyat
                        else:
                            tuketim = alet.watt * (alet.sure_dk / 60)
                            birim_fiyat = tarife.saat_fiyati_getir(baslangic_saati)
                        toplam_enerji_wh += tuketim
                        toplam_maliyet_tl += (tuketim / 1000) * birim_fiyat
        if toplam_enerji_wh == 0: user.score = 50; continue
        user_avg_maliyet = toplam_maliyet_tl / (toplam_enerji_wh / 1000)
        fiyat_araligi = max_fiyat - min_fiyat
        score = 100 if fiyat_araligi == 0 else ((max_fiyat - user_avg_maliyet) / fiyat_araligi) * 100
        user.score = round(max(0, min(100, score)), 2)
        print(f"   👤 {user.isim}: Ort.Maliyet: {user_avg_maliyet:.2f} TL/kWh -> SKOR: {user.score}")


# --- 5. VERİTABANI ---
def veritabani_kur():
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS Sirketler (id INTEGER PRIMARY KEY, isim TEXT)")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY, isim TEXT, soyisim TEXT, sirket_id INTEGER, score REAL, FOREIGN KEY(sirket_id) REFERENCES Sirketler(id))")

    # --- YENİ ALAN: hedef_sicaklik ---
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
                       hedef_sicaklik
                       REAL,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES Users
                   (
                       id
                   )
                       )
                   """)

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS Aletler (id INTEGER PRIMARY KEY, tur TEXT, marka TEXT, watt INTEGER, ev_id INTEGER, FOREIGN KEY(ev_id) REFERENCES Evler(id))")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS TuketimLoglari (id INTEGER PRIMARY KEY AUTOINCREMENT, alet_id INTEGER, tarih TEXT, baslangic_saati TEXT, bitis_saati TEXT, tuketim_wh REAL, FOREIGN KEY(alet_id) REFERENCES Aletler(id))")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS Tarifeler (id INTEGER PRIMARY KEY AUTOINCREMENT, sirket_id INTEGER, t1_aralik TEXT, t1_fiyat REAL, t2_aralik TEXT, t2_fiyat REAL, t3_aralik TEXT, t3_fiyat REAL, FOREIGN KEY(sirket_id) REFERENCES Sirketler(id))")
    conn.commit();
    conn.close()


def verileri_kaydet(users, sirketler, tarifeler):
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()
    for s in sirketler: cursor.execute("INSERT OR REPLACE INTO Sirketler VALUES (?, ?)", (s.id, s.isim))
    for t in tarifeler: cursor.execute(
        "INSERT OR REPLACE INTO Tarifeler (sirket_id, t1_aralik, t1_fiyat, t2_aralik, t2_fiyat, t3_aralik, t3_fiyat) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (t.sirket_id, t.t1_gunduz[0], t.t1_gunduz[1], t.t2_puant[0], t.t2_puant[1], t.t3_gece[0], t.t3_gece[1]))
    for u in users:
        cursor.execute("INSERT OR REPLACE INTO Users VALUES (?, ?, ?, ?, ?)",
                       (u.id, u.isim, u.soyisim, u.sirket_id, u.score))
        for ev in u.evler:
            # --- YENİ ALAN KAYDI ---
            cursor.execute("INSERT OR REPLACE INTO Evler VALUES (?, ?, ?, ?, ?)",
                           (ev.id, ev.adres, u.id, ev.aylik_toplam_tuketim / 1000, ev.hedef_sicaklik))
            for alet in ev.ev_aletleri:
                cursor.execute("INSERT OR REPLACE INTO Aletler VALUES (?, ?, ?, ?, ?)",
                               (alet.id, alet.tur, alet.marka, alet.watt, ev.id))
                for tarih, logs in alet.gunluk_loglar.items():
                    for aralik in logs:
                        bas, bit = aralik.split('-')
                        tuk = alet.watt * 24 if alet.sure_dk == 1440 else alet.watt * (alet.sure_dk / 60)
                        cursor.execute(
                            "INSERT INTO TuketimLoglari (alet_id, tarih, baslangic_saati, bitis_saati, tuketim_wh) VALUES (?, ?, ?, ?, ?)",
                            (alet.id, tarih, bas, bit, tuk))
    conn.commit();
    conn.close()
    print("✅ Tüm veriler kaydedildi (Termostatlar dahil).")


if __name__ == "__main__":
    veritabani_kur()
    sirketler, tarifeler = sirket_datalari_olustur()
    users = kullanici_verileri_olustur(sirketler)
    kullanici_skorlarini_hesapla(users, tarifeler)
    verileri_kaydet(users, sirketler, tarifeler)