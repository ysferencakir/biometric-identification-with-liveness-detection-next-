# Biometric Identification — Backend

> **BLGM 405 Graduation Project** | Python · FastAPI · InsightFace · OpenCV · SQLite

---

## Sistem Mimarisi

```
Kamera Görüntüsü
      │
      ▼
  Preprocessing  (BGR→RGB, resize)
      │
      ▼
  FaceDetector   (InsightFace buffalo_l – GPU/CPU)
      │
      ▼
  Liveness Pipeline
  ┌───────────────────────────────┐
  │  Session → 2 Rastgele Modül  │
  │                               │
  │  BlinkDetector      (EAR)    │
  │  HeadMovementDetector (Yaw)  │
  │  MouthMovementDetector (MAR) │
  └───────────────┬───────────────┘
                  │ Her ikisi geçildi?
                  ▼
  FaceRecognition (ArcFace embedding + Cosine Similarity)
                  │
                  ▼
  DecisionEngine → ACCESS GRANTED / DENIED
```

---

## Klasör Yapısı

```
backend/
├── main.py                    # FastAPI uygulama girişi
├── config.py                  # Merkezi konfigürasyon
├── requirements.txt
│
├── api/
│   ├── routes.py              # Tüm endpoint handler'ları
│   └── schemas.py             # Pydantic request/response modelleri
│
├── core/
│   ├── detection.py           # InsightFace singleton wrapper
│   ├── recognition.py         # Yüz tanıma orchestrator
│   ├── preprocessing.py       # BGR→RGB, resize
│   ├── embedding.py           # L2-normalize, mean embedding
│   ├── similarity.py          # Cosine similarity
│   ├── decision_engine.py     # Liveness + Recognition → AccessDecision
│   └── liveness/
│       ├── base.py            # ABC — LivenessDetectorBase
│       ├── manager.py         # Registry + dispatcher
│       ├── blink_detector.py  # Göz kırpma (EAR, 68-point)
│       ├── head_movement.py   # Baş hareketi (Yaw proxy)
│       ├── mouth_movement.py  # Ağız hareketi (MAR, 68-point)
│       └── texture_analyzer.py # MiniFASNet (domain shift sorunu — ertelendi)
│
├── db/
│   └── store.py               # SQLite CRUD (users, sessions, audit_log)
│
├── utils/
│   ├── image.py               # Base64 ↔ ndarray
│   └── constants.py           # Eşik değerleri
│
├── models/
│   └── anti_spoofing/         # MiniFASNet .pth dosyaları
│
└── scripts/
    ├── test_e2e.py            # E2E API testleri (14/14)
    ├── test_performance.py    # Latency ölçümleri
    ├── test_blink_live.py     # BlinkDetector webcam testi
    ├── test_head_live.py      # HeadMovementDetector webcam testi
    ├── test_mouth_live.py     # MouthMovementDetector webcam testi
    └── test_texture_live.py   # TextureAnalyzer webcam testi
```

---

## Kurulum

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

---

## Çalıştırma

```bash
.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- ReDoc:      `http://localhost:8000/redoc`

---

## API Endpoint'leri

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/v1/health` | Sistem sağlık kontrolü |
| POST | `/api/v1/register` | Kullanıcı kaydı (5+ frame) |
| POST | `/api/v1/recognize` | Yüz tanıma (base64) |
| GET | `/api/v1/users` | Kullanıcı listesi |
| DELETE | `/api/v1/users/{id}` | Kullanıcı sil |
| POST | `/api/v1/session/create` | Yeni doğrulama session'ı (2 rastgele modül) |
| GET | `/api/v1/session/{id}` | Session durumu |
| GET | `/api/v1/liveness/available` | Kayıtlı liveness modülleri |
| POST | `/api/v1/liveness/submit` | Liveness frame gönder |
| POST | `/api/v1/verify` | Biyometrik doğrulama |

Tam dokümantasyon: `docs/API_CONTRACT.md`

---

## Liveness Modülleri

| Modül | Yöntem | Durum |
|-------|--------|-------|
| `BlinkDetector` | EAR < 0.23, 68-point landmark | ✅ Aktif |
| `HeadMovementDetector` | Yaw proxy (sağ+sol) | ✅ Aktif |
| `MouthMovementDetector` | MAR > 0.55, 68-point landmark | ✅ Aktif |
| `TextureAnalyzer` | MiniFASNet ensemble | ⚠️ Domain shift — ertelendi |

Session başına **rastgele 2 modül** seçilir (`LIVENESS_CHALLENGES_COUNT=2`).

---

## Performans (CPU — RTX 4070 mevcut değil)

| İşlem | Ortalama |
|-------|----------|
| Session oluşturma | 25ms |
| Liveness submit | 422ms |
| Recognize | 388ms |

---

## Veritabanı Şeması

```sql
users              -- kayıtlı kullanıcılar + ArcFace embedding
sessions           -- doğrulama session'ları
liveness_challenges -- her challenge frame sonucu
audit_log          -- access_granted / access_denied / session_created
```
