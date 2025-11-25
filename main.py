import sqlite3
import random
import time
from datetime import datetime

# --- 1. AYARLAR ---
random.seed()

# --- 2. KATALOG (Orijinal Koddan) ---
CIHAZ_KATALOGU = {
    "Bosch": {
        "Buzdolabı": {"watt": 150, "tip": "sabit"},
        "Fırın": {"watt": 2200, "tip": "manuel"}
    },
    "Samsung": {
        "TV": {"watt": 120, "tip": "sik"},
        "Klima": {"watt": 1500, "tip": "mevsimsel"}
    },
    "Arçelik": {
        "Ütü": {"watt": 2400, "tip": "manuel"},
        "Çay Makinası": {"watt": 1800, "tip": "sik"}
    },
    "Dyson": {
        "Süpürge": {"watt": 600, "tip": "manuel"}
    }
}


# --- 3. VERİTABANI İŞLEMLERİ ---
def veritabani_kontrol_ve_eklenti():
    """
    Mevcut veritabanı yapısını BOZMADAN,
    sadece canlı takip için yeni bir tablo ekler.
    """
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()

    # Mevcut tabloların varlığını kontrol et (Orijinal yapının kurulu olduğundan emin olmak için)
    try:
        cursor.execute("SELECT count(*) FROM Aletler")
    except sqlite3.OperationalError:
        print(
            "⚠️ UYARI: Orijinal tablolar bulunamadı. Lütfen önce eski main.py'yi bir kez çalıştırıp veritabanını oluşturun.")
        return

    # --- YENİ TABLO ---
    # Sadece anlık durumları tutar. Aletler tablosuna dokunmaz.
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS CihazDurumlari
                   (
                       alet_id
                       INTEGER
                       PRIMARY
                       KEY,
                       calisiyor_mu
                       INTEGER,
                       anlik_tuketim
                       REAL,
                       son_guncelleme
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       alet_id
                   ) REFERENCES Aletler
                   (
                       id
                   )
                       )
                   """)

    conn.commit()
    conn.close()
    print("✅ Veritabanı yapısı korundu, 'CihazDurumlari' tablosu hazırlandı.")


def simulasyon_tick():
    """Dakikada bir çalışan ana döngü."""
    conn = sqlite3.connect("enerji_takip.db")
    cursor = conn.cursor()

    # 1. Orijinal tablodan statik verileri çek (Watt, Tür vb.)
    cursor.execute("SELECT id, tur, marka, watt FROM Aletler")
    aletler = cursor.fetchall()

    sim_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔄 Simülasyon: {sim_time} - {len(aletler)} cihaz güncelleniyor...")

    for alet in aletler:
        alet_id, tur, marka, nominal_watt = alet

        # --- Zeka / Olasılık Mantığı ---
        calisma_olasiligi = 0.1

        if tur == "Buzdolabı":
            calisma_olasiligi = 0.95
        elif tur in ["TV", "Klima", "Çay Makinası"]:
            calisma_olasiligi = 0.35
        elif tur in ["Ütü", "Süpürge", "Fırın"]:
            calisma_olasiligi = 0.05

        # Zar at
        calisiyor = 1 if random.random() < calisma_olasiligi else 0

        # Tüketim Hesapla (Hafif dalgalanma efekti ver)
        anlik_tuketim = 0
        if calisiyor:
            variation = random.uniform(0.9, 1.1)  # %10 sapma
            anlik_tuketim = nominal_watt * variation

        # --- YENİ TABLOYA YAZ (Eskisine dokunma) ---
        # INSERT OR REPLACE: Varsa günceller, yoksa ekler.
        cursor.execute("""
            INSERT OR REPLACE INTO CihazDurumlari (alet_id, calisiyor_mu, anlik_tuketim, son_guncelleme)
            VALUES (?, ?, ?, ?)
        """, (alet_id, calisiyor, round(anlik_tuketim, 2), sim_time))

        # İsteğe bağlı: Geçmiş loglara da ekleyelim (Opsiyonel)
        if calisiyor:
            # Orijinal TuketimLoglari yapısına uygun veri ekleme
            # Not: Orijinal yapıda 'baslangic_saati' ve 'bitis_saati' text formatındaydı.
            saat_dilimi = datetime.now().strftime("%H:%M")
            cursor.execute(
                "INSERT INTO TuketimLoglari (alet_id, tarih, baslangic_saati, bitis_saati, tuketim_wh) VALUES (?, ?, ?, ?, ?)",
                (alet_id, datetime.now().strftime("%d.%m.%Y"), saat_dilimi, saat_dilimi, anlik_tuketim / 60))

    conn.commit()
    conn.close()
    print("✅ Durumlar güncellendi.")


if __name__ == "__main__":
    veritabani_kontrol_ve_eklenti()

    print("🚀 Simülasyon Modu Başlatıldı (Kapatmak için CTRL+C)")
    try:
        while True:
            simulasyon_tick()
            time.sleep(60)  # 1 Dakika bekle
    except KeyboardInterrupt:
        print("🛑 Simülasyon durduruldu.")