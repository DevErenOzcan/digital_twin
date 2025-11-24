import sqlite3
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Tarayıcı erişimine izin ver


def get_db_connection():
    # main.py'nin oluşturduğu veritabanı dosyasına bağlanıyoruz
    conn = sqlite3.connect('enerji_takip.db')
    conn.row_factory = sqlite3.Row
    return conn


# --- 1. GENEL VERİ (MAHALLE GÖRÜNÜMÜ) ---
@app.route('/api/digital-twin', methods=['GET'])
def get_digital_twin_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kullanıcıları, evlerini ve skorlarını çekiyoruz
    # u.id'yi özellikle seçiyoruz çünkü detay isterken bu ID lazım olacak
    query = """
            SELECT u.id, u.isim, u.soyisim, u.score, e.adres, e.toplam_tuketim_kwh
            FROM Users u
                     JOIN Evler e ON u.id = e.user_id \
            """
    rows = cursor.execute(query).fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id": row["id"],  # Veritabanındaki gerçek User ID
            "isim": row["isim"],
            "soyisim": row["soyisim"],
            "score": row["score"],
            "adres": row["adres"],
            "tuketim": row["toplam_tuketim_kwh"]
        })

    return jsonify(data)


# --- 2. DETAY VERİSİ (EVE TIKLAYINCA AÇILAN ANALİZ) ---
@app.route('/api/details/<int:user_id>', methods=['GET'])
def get_house_details(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Kullanıcının evindeki aletleri çek
    query_aletler = """
                    SELECT a.id, a.tur, a.marka, a.watt
                    FROM Aletler a
                             JOIN Evler e ON a.ev_id = e.id
                    WHERE e.user_id = ? \
                    """
    aletler = cursor.execute(query_aletler, (user_id,)).fetchall()

    detaylar = []

    for alet in aletler:
        # 2. Her aletin tüketim loglarını çekip analiz et
        query_log = """
                    SELECT baslangic_saati, tuketim_wh \
                    FROM TuketimLoglari \
                    WHERE alet_id = ? \
                    """
        logs = cursor.execute(query_log, (alet['id'],)).fetchall()

        toplam_tuketim = 0
        puant_kullanim_sayisi = 0  # 17:00 - 22:00 arası
        gece_kullanim_sayisi = 0  # 22:00 - 06:00 arası
        toplam_calisma = 0

        for log in logs:
            tuketim = log['tuketim_wh']
            try:
                # Log verisi bazen "18" bazen "18.30" olabilir, integer'a çeviriyoruz
                bas_str = str(log['baslangic_saati']).split('.')[0]
                baslangic = int(bas_str)
            except:
                baslangic = 12  # Hata durumunda varsayılan

            toplam_tuketim += tuketim
            toplam_calisma += 1

            # --- ANALİZ MANTIĞI ---
            if 17 <= baslangic < 22:
                puant_kullanim_sayisi += 1
            elif baslangic >= 22 or baslangic < 6:
                gece_kullanim_sayisi += 1

        # Durum Etiketi Belirleme
        durum = "Normal"
        if toplam_calisma > 0:
            puant_orani = puant_kullanim_sayisi / toplam_calisma
            gece_orani = gece_kullanim_sayisi / toplam_calisma

            if puant_orani > 0.4:  # Kullanımın %40'ı pahalı saatteyse
                durum = "Fazla Tüketim"
            elif gece_orani > 0.4:  # Kullanımın %40'ı ucuz saatteyse
                durum = "Verimli"

            # Buzdolabı özel durumu
            if alet['tur'] == "Buzdolabı":
                durum = "Sabit Yük"

        detaylar.append({
            "tur": alet['tur'],
            "marka": alet['marka'],
            "tuketim_kwh": round(toplam_tuketim / 1000, 2),
            "durum": durum
        })

    conn.close()
    return jsonify(detaylar)


if __name__ == '__main__':
    print("🌍 Digital Twin API Çalışıyor: http://127.0.0.1:5000")
    print("⚠️ Önce 'python main.py' dosyasını çalıştırıp veritabanını oluşturduğundan emin ol.")
    app.run(debug=True, port=5000)