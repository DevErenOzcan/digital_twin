import sqlite3
import requests
import random
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# API KEY'iniz varsa buraya yazın. Yoksa kod mock data üretecektir.
OPENWEATHER_API_KEY = "caf76a2f270d3cd2405280edd5c9306f"
CITY = "Manisa"


def get_db_connection():
    conn = sqlite3.connect('enerji_takip.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_live_weather():
    """Hava durumunu çeker. Hata alırsa rastgele veri döner."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data['main']['temp'],
                "desc": data['weather'][0]['description'],
                "is_live": True
            }
    except:
        pass

    # API yoksa veya hata verdiyse simülasyon yap
    return {
        "temp": random.uniform(5, 30),  # 5 ile 30 derece arası salla
        "desc": "Simülasyon (Parçalı Bulutlu)",
        "is_live": False
    }


@app.route('/api/digital-twin', methods=['GET'])
def get_digital_twin_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT u.id, u.isim, u.soyisim, u.score, e.adres, e.toplam_tuketim_kwh FROM Users u JOIN Evler e ON u.id = e.user_id"
    rows = cursor.execute(query).fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "isim": row["isim"],
            "soyisim": row["soyisim"],
            "score": row["score"],
            "adres": row["adres"],
            "tuketim": row["toplam_tuketim_kwh"]
        })
    return jsonify(data)


@app.route('/api/details/<int:user_id>', methods=['GET'])
def get_house_details(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Aletleri Çek
    query_aletler = "SELECT a.id, a.tur, a.marka, a.watt FROM Aletler a JOIN Evler e ON a.ev_id = e.id WHERE e.user_id = ?"
    aletler = cursor.execute(query_aletler, (user_id,)).fetchall()

    # 2. Evin Termostat Hedef Sıcaklığını Çek
    query_ev = "SELECT hedef_sicaklik FROM Evler WHERE user_id = ?"
    ev_data = cursor.execute(query_ev, (user_id,)).fetchone()
    hedef_sicaklik = ev_data['hedef_sicaklik'] if ev_data else 22

    # 3. Hava Durumunu Al
    weather = get_live_weather()
    dis_sicaklik = weather['temp']

    # 4. Termostat Mantığı
    termostat_durumu = "Beklemede"
    if dis_sicaklik < (hedef_sicaklik - 1):
        termostat_durumu = "Isıtıyor 🔥"
    elif dis_sicaklik > (hedef_sicaklik + 1):
        termostat_durumu = "Soğutuyor ❄️"

    termostat_info = {
        "tur": "Termostat",
        "marka": "IoT Smart",
        "hedef": hedef_sicaklik,
        "dis_hava": round(dis_sicaklik, 1),
        "durum": termostat_durumu,
        "is_live": weather['is_live'],
        "desc": weather['desc']
    }

    detaylar = []
    # Termostatı listenin başına ekle
    detaylar.append(termostat_info)

    for alet in aletler:
        query_log = "SELECT baslangic_saati, tuketim_wh FROM TuketimLoglari WHERE alet_id = ?"
        logs = cursor.execute(query_log, (alet['id'],)).fetchall()

        toplam_tuketim = 0
        puant_kullanim = 0;
        gece_kullanim = 0;
        toplam_calisma = 0

        for log in logs:
            tuketim = log['tuketim_wh']
            try:
                baslangic = int(str(log['baslangic_saati']).split('.')[0])
            except:
                baslangic = 12
            toplam_tuketim += tuketim
            toplam_calisma += 1
            if 17 <= baslangic < 22:
                puant_kullanim += 1
            elif baslangic >= 22 or baslangic < 6:
                gece_kullanim += 1

        durum = "Normal"
        if toplam_calisma > 0:
            if (puant_kullanim / toplam_calisma) > 0.4:
                durum = "Savurgan"
            elif (gece_kullanim / toplam_calisma) > 0.4:
                durum = "Verimli"
        if alet['tur'] == "Buzdolabı": durum = "Sabit Yük"

        detaylar.append({
            "tur": alet['tur'],
            "marka": alet['marka'],
            "tuketim_kwh": round(toplam_tuketim / 1000, 2),
            "durum": durum
        })

    conn.close()
    return jsonify(detaylar)


if __name__ == '__main__':
    print("🌍 Digital Twin API + Weather Çalışıyor: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)