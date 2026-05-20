# Biometric Identification with Liveness Detection

> **BLGM 405 — Proje Yönetimi ve Geliştirme**  
> **Dönem:** Güz 2025 | **Danışman:** Adnan Acan  
> **Bitiş:** 01.06.2026

---

## Proje Özeti

Yüz tanıma tabanlı kimlik doğrulama sistemlerine **aktif liveness detection** ekleyen web tabanlı prototip.  
Fotoğraf, video veya ekran gösterimi ile yapılan spoofing saldırılarını engeller.

---

## Ekip

| Kişi | Rol |
|------|-----|
| **Mithatcan Sonsuz** | Proje Yöneticisi · Backend Core · DB · Session API |
| **Yusuf Eren Çakır** | Backend ML · Liveness Modülleri |
| **İsmail Sefa Çim** | Full-Stack · Frontend · Test UI |

---

## Sistem Akışı

```
Kullanıcı → Kamera
     │
     ▼
Session Oluştur (2 rastgele liveness modülü seçilir)
     │
     ├─► Liveness Challenge 1  (blink / head / mouth)
     │         ↓ passed?
     ├─► Liveness Challenge 2  (blink / head / mouth)
     │         ↓ passed?
     ▼
Biyometrik Doğrulama (InsightFace ArcFace)
     │
     ▼
ACCESS GRANTED / DENIED
```

---

## Teknoloji Yığını

### Backend
- **Python 3.11** · FastAPI · Uvicorn
- **InsightFace** (buffalo_l) — yüz tespiti + ArcFace embedding
- **SQLite** — kullanıcılar, session'lar, audit log
- **OpenCV** — görüntü işleme

### Frontend
- **Next.js 16** · TypeScript · Tailwind CSS
- `MediaDevices.getUserMedia` — kamera erişimi

### Liveness Modülleri
| Modül | Yöntem |
|-------|--------|
| `BlinkDetector` | EAR (Eye Aspect Ratio) — 68-point landmark |
| `HeadMovementDetector` | Yaw proxy — sağ + sol baş dönüşü |
| `MouthMovementDetector` | MAR (Mouth Aspect Ratio) — ağız aç/kapat |

---

## Çalıştırma

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
node node_modules/next/dist/bin/next dev --port 3000
```

### Sayfalar
| URL | Açıklama |
|-----|----------|
| `http://localhost:3000` | Ana sayfa |
| `http://localhost:3000/register` | Kullanıcı kaydı |
| `http://localhost:3000/verify` | Kimlik doğrulama |
| `http://localhost:3000/test-ui` | Liveness modül testi |
| `http://localhost:8000/docs` | Swagger API |

---

## Test

```bash
cd backend
# E2E API testleri
.venv\Scripts\python.exe scripts/test_e2e.py          # 14/14 PASS

# Performans testleri
.venv\Scripts\python.exe scripts/test_performance.py

# Liveness modül testleri (webcam)
.venv\Scripts\python.exe scripts/test_blink_live.py
.venv\Scripts\python.exe scripts/test_head_live.py
.venv\Scripts\python.exe scripts/test_mouth_live.py
```

---

## Proje Yapısı

```
biometric-identification/
├── backend/          # Python/FastAPI backend
│   ├── core/         # İş mantığı (detection, recognition, liveness)
│   ├── api/          # Endpoint'ler ve schema'lar
│   ├── db/           # SQLite CRUD
│   ├── scripts/      # Test ve yardımcı scriptler
│   └── models/       # Anti-spoofing model dosyaları
├── frontend/         # Next.js frontend
│   ├── app/          # Sayfalar (verify, register, test-ui)
│   ├── components/   # CameraFeed
│   └── lib/          # API client, kamera utilities
└── docs/             # API sözleşmesi
    └── API_CONTRACT.md
```

---

## Dokümantasyon

- [API Sözleşmesi](docs/API_CONTRACT.md)
- [Backend README](backend/README.md)
- [Geliştirme Planı](GELISTIRME_PLANI.md)

---

## Bilinen Kısıtlar

| Konu | Durum |
|------|-------|
| TextureAnalyzer (MiniFASNet) | Domain shift sorunu — Sprint 7'de ele alınacak |
| Voice Challenge | Ertelendi — Whisper entegrasyonu gerekli |
| GPU desteği | CPU fallback aktif (CUDA yoksa) |
