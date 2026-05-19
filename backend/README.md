# Biometric Identification – Face Recognition Module

> **Graduation Project** | Python · FastAPI · InsightFace (ArcFace) · OpenCV · SQLite

---

## Proje Genel Bakış

Bu backend, **Face Detection & Face Recognition** alt sistemini uçtan uca çalışır hale getirir.  
Liveness detection modülünden **bağımsız** çalışacak şekilde tasarlanmıştır; final erişim kararı ileride `core/decision_engine.py` içinde birleştirilecektir.

```
Kamera Görüntüsü
      │
      ▼
  Preprocessing  (BGR→RGB, resize)
      │
      ▼
  FaceDetector   (InsightFace – GPU / CPU fallback)
      │
  ┌───┴───────────────────────┐
  │                           │
  0 yüz                    1 yüz                   >1 yüz
  │                           │                       │
  ▼                           ▼                       ▼
No Face             Embedding Extract           Multiple Faces
                        │
                        ▼
                  Cosine Similarity ── DB Users
                        │
                ┌───────┴───────┐
                │               │
            score ≥ th       score < th
                │               │
            Recognized       Unknown
```

---

## Klasör Yapısı

```
backend/
├── main.py                  # FastAPI uygulama giriş noktası
├── config.py                # Merkezi konfigürasyon (.env okur)
├── .env.example             # Ortam değişkeni şablonu
├── requirements.txt
│
├── api/
│   ├── routes.py            # Tüm endpoint handler'ları
│   └── schemas.py           # Pydantic request/response modelleri
│
├── core/
│   ├── detection.py         # FaceDetector singleton (InsightFace wrapper)
│   ├── recognition.py       # Üst seviye orchestrator: detect→embed→compare
│   ├── preprocessing.py     # Frame doğrulama + BGR→RGB dönüşümü
│   ├── embedding.py         # L2-normalize + mean embedding
│   ├── similarity.py        # Cosine similarity + threshold
│   ├── decision_engine.py   # (Stub) Recognition + Liveness birleştirici
│   └── liveness/
│       ├── base.py          # ABC – her liveness algoritması bunu implemente eder
│       └── manager.py       # Liveness registry + dispatcher
│
├── db/
│   └── store.py             # SQLite CRUD (sqlite3 built-in)
│
├── utils/
│   ├── image.py             # Base64 ↔ ndarray, resize helpers
│   └── constants.py         # Eşik değerleri, mesajlar (tek kaynak)
│
└── scripts/
    ├── live_recognition.py  # Gerçek zamanlı test istemcisi
    └── register_user.py     # Kullanıcı kayıt scripti
```

---

## Kurulum

### 1. Sanal ortam oluştur

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
```

### 2. Temel bağımlılıkları yükle

```powershell
pip install -r requirements.txt
```

### 3. ONNX Runtime kur (GPU veya CPU seç)

**RTX 4070 (CUDA 12.x) için — önerilen:**
```powershell
pip install onnxruntime-gpu==1.18.0
```

**Sadece CPU:**
```powershell
pip install onnxruntime==1.18.0
```

> ⚠️ `onnxruntime` ve `onnxruntime-gpu` aynı anda kurulmamalı. Birini kaldır: `pip uninstall onnxruntime`

### 4. CUDA araçlarını doğrula (opsiyonel)

```powershell
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Beklenen çıktı: ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

### 5. .env dosyasını oluştur

```powershell
copy .env.example .env
# Gerekirse değerleri düzenle
```

---

## Çalıştırma

### Backend'i başlat

```powershell
# Sanal ortam aktifken:
python main.py

# Veya uvicorn ile:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

---

## Kullanıcı Kaydetme

### Script ile (önerilen)

```powershell
# Manuel SPACE ile çekme:
python scripts/register_user.py --name "Mithat"

# Otomatik yakalama (1 frame/sn):
python scripts/register_user.py --name "Mithat" --auto

# Farklı kamera veya frame sayısı:
python scripts/register_user.py --name "Mithat" --cam 1 --frames 8
```

### API ile (curl / Postman)

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Mithat", "frames": ["<base64_frame_1>", "<base64_frame_2>", ...]}'
```

---

## Gerçek Zamanlı Tanıma

```powershell
python scripts/live_recognition.py

# Farklı kamera:
python scripts/live_recognition.py --cam 1

# FPS sınırı:
python scripts/live_recognition.py --fps-cap 10
```

| Renk | Anlam |
|------|-------|
| 🟢 Yeşil kutu + isim | Kullanıcı tanındı |
| 🔴 Kırmızı kutu | Yüz var ama tanınmadı |
| Kutu yok | Yüz yok veya birden fazla yüz |

---

## API Referansı

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/api/v1/health` | Sistem durumu |
| `POST` | `/api/v1/recognize` | Base64 frame → tanıma sonucu |
| `POST` | `/api/v1/recognize/upload` | Dosya yükleme → tanıma sonucu |
| `POST` | `/api/v1/register` | Yeni kullanıcı kaydet |
| `GET` | `/api/v1/users` | Kayıtlı kullanıcı listesi |
| `DELETE` | `/api/v1/users/{id}` | Kullanıcı sil |

### Örnek Response'lar

**Tanınan kullanıcı:**
```json
{
  "face_detected": true,
  "face_count": 1,
  "recognized": true,
  "user_id": "a1b2c3...",
  "name": "Mithat",
  "recognition_score": 0.87,
  "bbox": [120, 80, 200, 220],
  "message": "User recognized"
}
```

**Bilinmeyen yüz:**
```json
{
  "face_detected": true,
  "face_count": 1,
  "recognized": false,
  "user_id": null,
  "name": null,
  "recognition_score": 0.32,
  "bbox": [120, 80, 200, 220],
  "message": "Unknown face"
}
```

---

## Eşik (Threshold) Ayarı

`utils/constants.py` → `RECOGNITION_THRESHOLD = 0.45`

| Değer | Etki |
|-------|------|
| `0.35` | Daha gevşek – yanlış pozitif artar |
| `0.45` | Varsayılan – iyi denge (ArcFace/buffalo_l için önerilen) |
| `0.55` | Daha katı – yanlış negatif artar |

---

## Decision Engine (İlerideki Entegrasyon)

`core/decision_engine.py` şu an recognition sonucunu direkt iletir.  
Liveness modülü hazır olduğunda yalnızca bu dosya değiştirilecek:

```python
# Şu an:
def decide(recognition: RecognitionResult) -> AccessDecision: ...

# İleride:
def decide(recognition: RecognitionResult, liveness: LivenessResult) -> AccessDecision: ...
```

Recognition modülü bu değişiklikten **etkilenmez**.

---

## Mimari Notlar

- **`recognition.py`** liveness'tan tamamen bağımsızdır – yalnızca "bu yüz kime ait?" sorusunu yanıtlar
- Embedding'ler SQLite'da raw `float32` bytes olarak saklanır (hız + sadelik)
- `FaceDetector` singleton'dır – model startup'ta bir kez yüklenir
- GPU yoksa veya CUDA başarısız olursa CPU'ya otomatik fallback yapılır
- `constants.py` tek kaynak gerçeği olarak tüm eşik değerlerini tutar
