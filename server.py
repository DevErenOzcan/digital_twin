import sqlite3
import requests
import random
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OPENWEATHER_API_KEY = "caf76a2f270d3cd2405280edd5c9306f"
CITY = "Manisa"


def get_db_connection():
    conn = sqlite3.connect('enerji_takip.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_live_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {"temp": data['main']['temp'], "desc": data['weather'][0]['description'], "is_live": True}
    except:
        pass
    return {"temp": random.uniform(18, 24), "desc": "Simülasyon", "is_live": False}


@app.route('/api/digital-twin', methods=['GET'])
def get_digital_twin_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kullanıcı ve Ev bilgilerini çek
    query = "SELECT u.id, u.isim, u.soyisim, u.score, e.adres, e.id as ev_id FROM Users u JOIN Evler e ON u.id = e.user_id"
    rows = cursor.execute(query).fetchall()

    data = []
    for row in rows:
        ev_id = row['ev_id']

        # --- CANLI TÜKETİM HESABI ---
        # Aletler tablosu ile CihazDurumlari tablosunu birleştirip topluyoruz
        live_query = """
                     SELECT SUM(d.anlik_tuketim) as toplam_watt
                     FROM Aletler a
                              JOIN CihazDurumlari d ON a.id = d.alet_id
                     WHERE a.ev_id = ? \
                       AND d.calisiyor_mu = 1 \
                     """
        res = cursor.execute(live_query, (ev_id,)).fetchone()

        anlik_watt = res['toplam_watt'] if res['toplam_watt'] else 0

        data.append({
            "id": row["id"],
            "isim": row["isim"],
            "soyisim": row["soyisim"],
            "score": row["score"],
            "adres": row["adres"],
            "anlik_tuketim_watt": round(anlik_watt, 1)  # KWh değil, Watt cinsinden anlık güç
        })
    conn.close()
    return jsonify(data)


@app.route('/api/details/<int:user_id>', methods=['GET'])
def get_house_details(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- 1. ALETLERİ VE CANLI DURUMLARINI ÇEK ---
    # LEFT JOIN kullanıyoruz: Eğer simülasyon henüz o alet için veri üretmediyse NULL gelmesin diye COALESCE kullanıyoruz.
    query_aletler = """
                    SELECT a.id, \
                           a.tur, \
                           a.marka, \
                           a.watt                       as nominal_watt, \
                           COALESCE(d.calisiyor_mu, 0)  as calisiyor_mu, \
                           COALESCE(d.anlik_tuketim, 0) as anlik_tuketim
                    FROM Aletler a
                             JOIN Evler e ON a.ev_id = e.id
                             LEFT JOIN CihazDurumlari d ON a.id = d.alet_id
                    WHERE e.user_id = ? \
                    """
    aletler = cursor.execute(query_aletler, (user_id,)).fetchall()

    # 2. Evin Hedef Sıcaklığı
    query_ev = "SELECT hedef_sicaklik FROM Evler WHERE user_id = ?"
    ev_data = cursor.execute(query_ev, (user_id,)).fetchone()
    hedef_sicaklik = ev_data['hedef_sicaklik'] if ev_data else 22

    # 3. Hava Durumu
    weather = get_live_weather()
    dis_sicaklik = weather['temp']

    # 4. Termostat Mantığı
    termostat_durumu = "Beklemede"
    if dis_sicaklik < (hedef_sicaklik - 1):
        termostat_durumu = "Isıtıyor 🔥"
    elif dis_sicaklik > (hedef_sicaklik + 1):
        termostat_durumu = "Soğutuyor ❄️"

    detaylar = []
    detaylar.append({
        "tur": "Termostat",
        "marka": "IoT Smart",
        "hedef": hedef_sicaklik,
        "dis_hava": round(dis_sicaklik, 1),
        "durum": termostat_durumu,
        "calisiyor_mu": True,
        "anlik_tuketim": 0
    })

    for alet in aletler:
        durum_metni = "KAPALI"
        if alet['calisiyor_mu']:
            durum_metni = "ÇALIŞIYOR"

        detaylar.append({
            "tur": alet['tur'],
            "marka": alet['marka'],
            "nominal_watt": alet['nominal_watt'],
            "anlik_tuketim": round(alet['anlik_tuketim'], 1),
            "calisiyor_mu": bool(alet['calisiyor_mu']),
            "durum": durum_metni
        })

    conn.close()
    return jsonify(detaylar)


if __name__ == '__main__':
    print("🌍 Live Digital Twin API (Non-Destructive Mode) Çalışıyor: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', debug=True, port=5000)