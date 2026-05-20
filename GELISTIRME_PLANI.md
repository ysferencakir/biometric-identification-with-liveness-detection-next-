# Biometric Identification with Liveness Detection — Geliştirme Planı

> **Son Güncelleme:** 2026-05-19  
> **Proje Durumu:** 🟡 Aktif Geliştirme  
> **Bitiş Tarihi:** 01.06.2026

---

## Geliştirici Atamaları

| Kişi | Rol | Sorumluluk |
|---|---|---|
| **Mithatcan Sonsuz** | Proje Yöneticisi / Backend Core | DB, Session, Decision Engine, API |
| **Yusuf Eren Çakır** | Backend ML | Liveness modülleri (BlinkDetector, HeadMovement, Texture) |
| **İsmail Sefa Çim** | Full-Stack | Next.js frontend, Test UI, WebSocket kamera akışı |

---

## Mevcut Mimari Özeti

Backend Python/FastAPI olarak `backend/` altında çalışır durumda.

| Modül | Dosya | Durum |
|---|---|---|
| FastAPI App | `backend/main.py` | ✅ Hazır |
| API Routes | `backend/api/routes.py` | ✅ Hazır |
| API Schemas | `backend/api/schemas.py` | ✅ Hazır |
| Yüz Tespiti | `backend/core/detection.py` | ✅ InsightFace singleton |
| Yüz Tanıma | `backend/core/recognition.py` | ✅ Hazır |
| Embedding | `backend/core/embedding.py` | ✅ ArcFace/L2 |
| Similarity | `backend/core/similarity.py` | ✅ Cosine |
| Preprocessing | `backend/core/preprocessing.py` | ✅ Hazır |
| Liveness Base | `backend/core/liveness/base.py` | ✅ ABC tanımlı |
| Liveness Manager | `backend/core/liveness/manager.py` | ✅ Registry var |
| Decision Engine | `backend/core/decision_engine.py` | ⚠️ Stub — liveness entegrasyonu eksik |
| Veritabanı | `backend/db/store.py` | ✅ SQLite CRUD |
| Kayıt Scripti | `backend/scripts/register_user.py` | ✅ Hazır |
| Test İstemcisi | `backend/scripts/live_recognition.py` | ✅ Hazır |
| **Frontend** | `frontend/` | ❌ Henüz yok |

### Kritik Eksikler
- Liveness detection implementasyonları yok (base class var, concrete sınıf yok)
- Decision Engine liveness sonuçlarını kullanmıyor
- Session yönetimi yok
- Frontend yok
- Test arayüzü yok
- 2-rastgele-liveness seçim mekanizması yok

---

## Hedef Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                      │
│   /register  │  /test-ui  │  /dashboard  │  /verify         │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│                   BACKEND API (FastAPI)                       │
│  /api/register  /api/verify  /api/liveness/challenge         │
│  /api/liveness/submit  /api/session  /api/health             │
└──────┬────────────┬──────────────┬──────────────────────────┘
       │            │              │
┌──────▼──┐  ┌──────▼──────┐  ┌───▼─────────────────────────┐
│  CORE   │  │  LIVENESS   │  │   DECISION ENGINE            │
│(mevcut) │  │  MODÜLLER   │  │   (genişletilecek)           │
│detection│  │ BlinkDet.   │  │ 2 rastgele liveness seç      │
│recognit.│  │ HeadMove.   │  │ → her ikisi geçildi mi?      │
│embedding│  │ TextureAn.  │  │ → biyometrik doğrulama       │
│similarity  └─────────────┘  │ → ACCESS GRANT / DENY        │
└─────────┘                   └──────────────────────────────┘
       │                              │
┌──────▼──────────────────────────────▼─────────────────────┐
│                   VERİTABANI (SQLite)                        │
│  users  │  sessions  │  liveness_challenges  │  audit_log   │
└────────────────────────────────────────────────────────────┘
```

---

## Nihai Doğrulama Akışı

```
1. Kullanıcı test arayüzünü açar
2. POST /api/session/create → 2 rastgele liveness modülü seçilir
3. Liveness Challenge 1 (örn: BlinkDetector) → frame gönder → passed?
4. Liveness Challenge 2 (örn: TextureAnalyzer) → frame gönder → passed?
5. Her ikisi geçildi → POST /api/verify → biyometrik doğrulama
6. ACCESS GRANTED veya ACCESS DENIED
```

---

## Modül Interface Sözleşmeleri

### Liveness Detector (tüm modüller bu ABC'yi implemente eder)

```python
# backend/core/liveness/base.py — DEĞİŞTİRİLMEZ

class LivenessDetectorBase(ABC):
    NAME: str = "base"  # Her detector benzersiz isim tanımlar

    def check(self, frame: np.ndarray, bbox: list[float]) -> LivenessResult: ...
    def get_instruction(self) -> str: ...
    def reset(self) -> None: ...

@dataclass
class LivenessResult:
    is_live: bool
    confidence: float          # 0.0 – 1.0
    detector_name: str
    challenge_completed: bool
    metadata: dict
```

### Yeni API Endpoint'leri

```
POST /api/session/create
  → { session_id, challenges: ["blink", "head_movement"], expires_at }

POST /api/liveness/submit
  Body: { session_id, challenge_name, frame: base64 }
  → { passed, confidence, all_challenges_passed }

POST /api/verify
  Body: { session_id, frame: base64 }
  → { access_granted, matched_user, confidence, decision_reason }

GET  /api/session/{session_id}
  → session durumu, tamamlanan challengelar

GET  /api/liveness/available
  → kayıtlı liveness modülleri listesi
```

### Yeni DB Tabloları

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    challenges TEXT,           -- JSON: ["blink", "texture"]
    completed_challenges TEXT, -- JSON: []
    status TEXT DEFAULT 'active'
);

CREATE TABLE liveness_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    challenge_name TEXT,
    passed INTEGER,
    confidence REAL,
    latency_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    event_type TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Sprint Planı

### Sprint 1 — Altyapı & Sözleşmeler
**Tarih:** 01.10.2025 – 09.10.2025 (9 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 1.1 | .gitignore güncelle | Mithatcan | ✅ Tamamlandı |
| 1.2 | DB şeması: sessions, liveness_challenges, audit_log | Mithatcan | ✅ Tamamlandı |
| 1.3 | API sözleşmelerini belgele (`docs/API_CONTRACT.md`) | Mithatcan | ✅ Tamamlandı |
| 1.4 | `core/liveness/base.py` final — NAME + get_instruction() + reset() | Yusuf | ✅ Tamamlandı |
| 1.5 | Next.js projesi kur (`frontend/`) | İsmail | ✅ Tamamlandı |
| 1.6 | `CameraFeed.tsx` — getUserMedia temel bileşen | İsmail | ✅ Tamamlandı |

---

### Sprint 2 — Core Geliştirme
**Tarih:** 10.10.2025 – 10.11.2025 (31 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 2.1 | `POST /api/session/create` — 2 rastgele modül seçimi | Mithatcan | ✅ Tamamlandı |
| 2.2 | `POST /api/liveness/submit` endpoint | Mithatcan | ✅ Tamamlandı |
| 2.3 | Session store CRUD (`db/store.py` genişletildi) | Mithatcan | ✅ Tamamlandı |
| 2.4 | `BlinkDetector` implementasyonu (InsightFace 106 landmark) | Yusuf | ✅ Tamamlandı |
| 2.5 | `HeadMovementDetector` implementasyonu | Yusuf | ✅ Tamamlandı |
| 2.6 | Test UI `/test-ui` sayfası — modül bazlı test | İsmail | ✅ Tamamlandı |
| 2.7 | `LivenessChallenge.tsx` bileşeni | İsmail | ✅ Tamamlandı (verify/page.tsx içinde inline) |

---

### Sprint 3 — Algoritma & Entegrasyon
**Tarih:** 11.11.2025 – 08.12.2025 (28 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 3.1 | Decision Engine tam implementasyon (2-liveness + biometrik) | Mithatcan | ✅ Tamamlandı |
| 3.2 | `POST /api/verify` endpoint (liveness entegre) | Mithatcan | ✅ Tamamlandı |
| 3.3 | Audit log entegrasyonu | Mithatcan | ✅ Tamamlandı |
| 3.4 | `TextureAnalyzer` implementasyonu (LBP) | Yusuf | ✅ Tamamlandı |
| 3.5 | `liveness/manager.py` — auto-register tüm modüller | Yusuf | ✅ Tamamlandı |
| 3.6 | `/verify` sayfası — tam doğrulama akışı | İsmail | ✅ Tamamlandı |
| 3.7 | `ProgressStepper.tsx` + `ResultPanel.tsx` | İsmail | ✅ Tamamlandı (inline) |

---

### Sprint 4 — Prototip & Test
**Tarih:** 09.12.2025 – 18.02.2026 (72 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 4.1 | E2E: kayıt → liveness × 2 → biyometrik test senaryoları | Mithatcan | ✅ Tamamlandı (14/14 PASSED) |
| 4.2 | FAR/FRR ölçümü ve raporu | Mithatcan | ✅ Tamamlandı (session:25ms liveness:422ms recognize:388ms) |
| 4.3 | Spoofing test senaryoları (fotoğraf/video/maske) | Yusuf | ⏭️ Atlandı |
| 4.4 | Eşik optimizasyonu (`utils/constants.py`) | Yusuf | ⏭️ Atlandı |
| 4.5 | Cross-browser test (Chrome/Edge/Firefox) | İsmail | ⏭️ Atlandı |
| 4.6 | UI/UX iyileştirmeler | İsmail | ✅ Tamamlandı |
| 4.7 | `TextureAnalyzer` — MiniFASNet denendi, domain shift sorunu (webcam ↔ eğitim verisi uyumsuzluğu). Havuzdan çıkarıldı. | Yusuf | 🔴 Sprint 5'e taşındı |

---

### Sprint 5 — Gelişmiş Özellikler & Bütünleştirme

**TextureAnalyzer için uygun algoritma arayışı:**
- MiniFASNet: domain shift nedeniyle çalışmadı
- Denenecekler: FFT piksel grid tespiti + lokal varyans hybrid, DepthFAS, FAS-TD, domain adaptation ile fine-tune

---

### Sprint 5 — Web Arayüzü & Entegrasyon (eski)
**Tarih:** 19.02.2026 – 30.03.2026 (40 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 5.1 | Güvenlik denetimleri + güvenlik açığı kapatma | Mithatcan | ⬜ Bekliyor |
| 5.2 | Loglama sistemi doğrulaması | Mithatcan | ⬜ Bekliyor |
| 5.3 | MicroExpression modülü (opsiyonel — v2) | Yusuf | ⬜ Bekliyor |
| 5.4 | `/register` sayfası polish | İsmail | ⬜ Bekliyor |
| 5.5 | Danışmana demo sunumu | Tüm ekip | ⬜ Bekliyor |

---

### Sprint 6 — Gelişmiş Test & Bütünleştirme
**Tarih:** 31.03.2026 – 25.04.2026 (26 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 6.1 | 3D maske saldırı simülasyonları | Yusuf | ⬜ Bekliyor |
| 6.2 | Performans darboğazı analizi (FPS/latency) | Mithatcan | ⬜ Bekliyor |
| 6.3 | Entegrasyon sorunlarının giderilmesi | Tüm ekip | ⬜ Bekliyor |

---

### Sprint 7 — Final Test & Performans
**Tarih:** 26.04.2026 – 20.05.2026 (25 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 7.1 | Test planı hazırlama | Mithatcan | ⬜ Bekliyor |
| 7.2 | FMR/FRR/Accuracy hesaplamaları | Mithatcan | ⬜ Bekliyor |
| 7.3 | Liveness başarım testi (final) | Yusuf | ⬜ Bekliyor |
| 7.4 | Kullanıcı deneyimi testi | İsmail | ⬜ Bekliyor |

---

### Sprint 8 — Raporlama & Sunum
**Tarih:** 21.05.2026 – 01.06.2026 (12 gün)

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 8.1 | Final proje raporu | Tüm ekip | ⬜ Bekliyor |
| 8.2 | Test sonuçları grafikleri | Mithatcan | ⬜ Bekliyor |
| 8.3 | Sunum slaytları | Tüm ekip | ⬜ Bekliyor |
| 8.4 | Danışmanla final toplantı | Tüm ekip | ⬜ Bekliyor |

---

## Test Checklist

### Liveness Modülleri (Yusuf)
- [ ] `BlinkDetector.check()` — gerçek kamera karesi
- [ ] `BlinkDetector.check()` — fotoğraf spoofing testi
- [ ] `HeadMovementDetector` — sağ/sol/yukarı/aşağı
- [ ] `TextureAnalyzer` — LBP histogram doğruluğu
- [ ] Her modül latency < 200ms
- [ ] Her modül `reset()` sonrası temiz başlangıç

### Session & Decision Engine (Mithatcan)
- [ ] `POST /session/create` 2 benzersiz modül seçiyor
- [ ] Session timeout (5 dakika) çalışıyor
- [ ] Her iki liveness geçilince erişim veriliyor
- [ ] Bir liveness başarısızsa reddediliyor
- [ ] Audit log her kararı kaydediyor

### Frontend (İsmail)
- [ ] Kamera izni isteniyor
- [ ] Frame gönderimi çalışıyor
- [ ] Liveness talimatı ekranda görünüyor
- [ ] Adım göstergesi doğru ilerliyor
- [ ] ACCESS GRANTED yeşil, ACCESS DENIED kırmızı
- [ ] Chrome, Edge, Firefox

### Entegrasyon
- [ ] Kayıt → 2 Liveness → Biyometrik → ACCESS GRANTED
- [ ] Liveness 1 Fail → ACCESS DENIED (2. adıma geçilmiyor)
- [ ] Fotoğraf spoofing → ACCESS DENIED
- [ ] Video spoofing → ACCESS DENIED
- [ ] Tanınmayan yüz → ACCESS DENIED (liveness geçilse bile)

### Performans Hedefleri
- [ ] FAR < %5
- [ ] FRR < %10
- [ ] Fotoğraf saldırısı tespiti > %90
- [ ] Video saldırısı tespiti > %85
- [ ] Frame işleme < 200ms
- [ ] End-to-end latency < 500ms

---

## Frontend Dosya Yapısı

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx              ← Ana sayfa
│   ├── register/page.tsx     ← Kullanıcı kaydı
│   ├── verify/page.tsx       ← Tam doğrulama akışı
│   └── test-ui/page.tsx      ← Geliştirici test arayüzü
├── components/
│   ├── CameraFeed.tsx        ← getUserMedia + frame capture
│   ├── LivenessChallenge.tsx ← Talimat + geri sayım
│   ├── ProgressStepper.tsx   ← Adım göstergesi
│   ├── ResultPanel.tsx       ← Sonuç kartı
│   └── UserRegistration.tsx  ← Kayıt formu
├── lib/
│   ├── api.ts                ← fetch wrapper
│   └── camera.ts             ← frame capture utilities
├── types/
│   └── api.ts                ← TypeScript interface'leri
└── .env.local
    NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Liveness Modül Dosya Yapısı

```
backend/core/liveness/
├── base.py               ← MEVCUT — DEĞİŞTİRİLMEZ
├── manager.py            ← MEVCUT — sadece register() çağrıları ekle
├── blink_detector.py     ← YENİ (Yusuf)
├── head_movement.py      ← YENİ (Yusuf)
├── texture_analyzer.py   ← YENİ (Yusuf)
└── __init__.py           ← GÜNCELLE — tüm detector'ları register et
```

---

## Karar Motoru Mantığı

```python
# backend/core/decision_engine.py

def decide(session, liveness_results, recognition_result) -> AccessDecision:
    # Kural 1: Her iki liveness geçilmeli
    if not all(r.is_live for r in liveness_results):
        return AccessDecision(granted=False, reason="liveness_failed")

    # Kural 2: Ortalama liveness confidence > 0.7
    avg_conf = sum(r.confidence for r in liveness_results) / len(liveness_results)
    if avg_conf < 0.7:
        return AccessDecision(granted=False, reason="low_liveness_confidence")

    # Kural 3: Biyometrik eşiği geçilmeli
    if not recognition_result.recognized:
        return AccessDecision(granted=False, reason="face_not_recognized")

    return AccessDecision(granted=True, matched_user=recognition_result.user_id)
```

---

## Bilinen Hatalar

| # | Endpoint | Hata | Durum |
|---|---|---|---|
| 1 | `POST /liveness/submit` | Browser 500 hatası — `allow_credentials=False` + global exception handler ile çözüldü. | ✅ Çözüldü |
| 2 | `TextureAnalyzer` | Eğitim verisi olmadan saf LBP eşik tespiti yüksek kaliteli ekran/baskı spoofing'e karşı sınırlı. Sprint 4'te CNN tabanlı model ile güçlendirilecek. | 🟡 Bilinen Kısıt |

---

## Değişiklik Geçmişi

| Tarih | Değişiklik | Güncelleyen |
|---|---|---|
| 2026-05-19 | Plan oluşturuldu, mevcut mimari analiz edildi | Claude Code |
| 2026-05-19 | Sprint 1 başladı: .gitignore, base.py (NAME+get_instruction+reset), DB tabloları (sessions, liveness_challenges, audit_log) tamamlandı | Claude Code |
| 2026-05-19 | Sprint 1 tamamlandı: API_CONTRACT.md, Next.js frontend kurulumu, types/api.ts, lib/api.ts, lib/camera.ts, CameraFeed.tsx | Claude Code |
| 2026-05-19 | Sprint 2 kısmen: /session/create, /liveness/submit, /verify, /liveness/available endpoint'leri + session CRUD + frontend sayfaları (verify, register, test-ui) | Claude Code |
| 2026-05-19 | BlinkDetector + HeadMovementDetector tamamlandı. Decision Engine liveness entegrasyonu. Browser 500 hatası çözüldü. Tam E2E akış çalışıyor (Hoşgeldin Yusuf, skor 85.1%) | Claude Code |
