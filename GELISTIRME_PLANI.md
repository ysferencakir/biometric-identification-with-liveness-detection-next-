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
| 5.1 | Güvenlik denetimleri + güvenlik açığı kapatma | Mithatcan | ✅ Tamamlandı |
| 5.2 | Loglama sistemi doğrulaması | Mithatcan | ✅ Tamamlandı (24 grant, 8 deny, 712 challenge) |
| 5.3 | MicroExpression modülü (opsiyonel — v2) | Yusuf | 🔮 İlerde Yapılacak |
| 5.4 | `/register` sayfası polish | İsmail | ✅ Tamamlandı (UI/UX sprint 4.6'da yapıldı) |
| 5.5 | Danışmana demo sunumu | Tüm ekip | ⬜ Bekliyor |

---

### Araştırma Bulguları — Adaptasyon Planı

> Kaynak: Deep Research Report (2026-05-20)

#### Özet Bulgular

| Modül | Mevcut Sorun | Önerilen Çözüm | Öncelik |
|---|---|---|---|
| BlinkDetector | Sabit EAR eşiği (0.23) — yavaş kırpanlarda başarısız | Adaptive Modified EAR + state machine (kişiye özel kalibrasyon) | 🔴 Yüksek |
| HeadMovementDetector | Oran tabanlı yaw proxy — kamera açısına bağımlı | OpenCV solvePnP / solvePnPRefineLM | 🔴 Yüksek |
| MouthMovementDetector | Landmark indeksleri görsel doğrulanmadı | Inner-lip aperture + hysteresis + indeks overlay doğrulama | 🟡 Orta |
| TextureAnalyzer | Domain shift (MiniFASNet) | MobileNetV3 hafif PAD + replay heuristics | 🔴 Yüksek |
| VoiceChallenge | Henüz yok | Vosk Turkish (dar vocab) / faster-whisper small int8 | 🟡 Orta |

---

#### 3 Aşamalı Adaptasyon Yol Haritası

**AŞAMA 1 — Yeni model indirmeden iyileştirme**
```
BlinkDetector:
  - İlk 1-2 saniyede açık göz EAR istatistiklerini topla
  - Kişiye özel üst/alt kuantilden eşik türet
  - Sabit 0.23 yerine dinamik eşik
  - "açık→kapalı→açık" state machine (tek frame eşik değil)

HeadMovementDetector:
  - Mevcut landmark_3d_68 kullanarak OpenCV solvePnP
  - Stabil 6 nokta: burun ucu, göz köşeleri, ağız köşeleri, çene
  - Yaw/pitch/roll değerlerini oran yerine derece cinsinden ölç
  - solvePnPRansac + solvePnPRefineLM ile kararlı poz

MouthMovementDetector:
  - Overlay scripti ile landmark indekslerini görsel doğrula
  - Outer-lip yerine inner-lip (60-67) aperture kullan
  - İki eşikli hysteresis + kısa temporal smoothing ekle
```

**AŞAMA 2 — MediaPipe entegrasyonu**
```
Liveness için MediaPipe Face Landmarker ekle:
  - 478 3B landmark + blendshape + transformation matrix
  - InsightFace: SADECE yüz tanıma için (değişmez)
  - MediaPipe: SADECE liveness için (paralel çalışır)
  
Avantajlar:
  - Blink: iris normalize eyelid aperture (göz boyutundan bağımsız)
  - Mouth: jawOpen blendshape skoru (landmark indeksine mahkum değil)
  - Head: facial transformation matrix (solvePnP kalibrasyonu gerekmez)
  
Kurulum: pip install mediapipe (0.10.x → tasks API)
Model: face_landmarker.task (~30MB)
CPU tahmini: 10-25ms/frame
```

**AŞAMA 3 — Çok sinyalli PAD (TextureAnalyzer yeniden yazma)**
```
4 bileşenli karar motoru:

1. Hafif RGB PAD skoru
   - MobileNetV3 tabanlı light-weight-face-anti-spoofing
   - MiniFASNet yardımcı skor olarak kalabilir
   - kendi webcam verimizle fine-tune edilebilir

2. Replay/print heuristics
   - Moiré/frekans band anormalliği (FFT)
   - Ekran/kağıt kenar tespiti
   - Aşırı speküler glare
   - Düşük mikrodoku çeşitliliği

3. Geometry challenge consistency
   - "sağa bak → kırp → ağzını aç" sırasının gerçekten görülüp görülmediği
   - solvePnP + blink + mouth state tutarlılığı

4. Capture quality gate
   - Blur, yüz boyutu, pozlama, kırpma kalitesi kötüyse PAD kararı üretme

Veri seti önerileri (fine-tuning için):
  - CelebA-Spoof (625K görüntü, 10K kişi)
  - OULU-NPU (mobil ön kamera, farklı cihaz)
  - CASIA-SURF CeFA (3D saldırılar dahil)
  - UniAttackData (CVPR 2024, 28K video, 14 saldırı türü)
```

**VoiceChallenge Planı**
```
Dar vocabulary (sayılar): Vosk Turkish + grammar constraint
  - ~50MB model, ~300MB RAM
  - <300ms latency

Geniş vocabulary: faster-whisper small int8
  - CPU'da daha hızlı, int8 quantization
  - Türkçe için "small" tercih edilmeli

Ses + görüntü senkronizasyonu:
  - Kullanıcı konuşurken ağız hareketi var mı?
  - Ses enerjisi ile jaw motion kabaca hizalı mı?
  - → Replay/TTS saldırılarına karşı ek güvence

Opsiyonel: AASIST / RawNet2 ses anti-spoofing skoru
  - Hard reject değil, risk artırıcı sinyal olarak
```

---

#### Sprint 6 Görev Güncellemesi

| # | Görev | Öncelik | Kaynak |
|---|---|---|---|
| 6.1 | ✅ MouthMovementDetector (temel) | — | Tamamlandı |
| 6.2 | BlinkDetector → Temporal Dip + EMA baseline (kişiye özel) | 🔴 | ✅ Tamamlandı |
| 6.3 | HeadMovementDetector → Normalized Nose Offset | 🔴 | ✅ Tamamlandı |
| 6.4 | MouthMovementDetector → inner-lip + hysteresis | 🟡 | ✅ Tamamlandı |
| 6.5 | MediaPipe Face Landmarker entegrasyonu | 🟡 | ✅ Tamamlandı |
| 6.6 | TextureAnalyzer → çok sinyalli PAD | 🔴 | ⬜ Bekliyor |
| 6.8 | MouthMovement: jawOpen blendshape'i state machine'e dahil et | 🟡 | 🔮 Sonra |
| 6.7 | VoiceChallenge → Vosk/faster-whisper | 🟡 | 🔮 Ertelendi |

---

#### 6.5 MediaPipe Güçlendirme Planı

**Neden MediaPipe?**
- InsightFace `landmark_3d_68` → 68 nokta, yeterli ama sınırlı
- MediaPipe Face Landmarker → 478 nokta + blendshape + iris/pupil refinement
- Blink için iris normalize eyelid aperture → kişiden kişiye değişmiyor
- Mouth için `jawOpen` blendshape skoru → sparse landmark hatalarından bağımsız
- Head için `facial_transformation_matrix` → solvePnP kalibrasyonu gerekmez

**Mimari (InsightFace korunur):**
```
Frame gelir
  │
  ├── InsightFace (buffalo_l)  →  Yüz Tanıma + Embedding (DEĞİŞMEZ)
  │
  └── MediaPipe Face Landmarker  →  Liveness sinyalleri
        ├── 478 landmark
        ├── blendshape skorları (jawOpen, eyeBlinkLeft, eyeBlinkRight...)
        └── facial_transformation_matrix (baş pozu)
```

**Kurulum:**
```bash
pip install mediapipe  # zaten kurulu ama solutions API kaldırılmış
# Yeni tasks API için model dosyası gerekiyor (~30MB)
# face_landmarker.task — MediaPipe model zoo'dan indirilir
```

**Model indirme:**
```bash
wget -q https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

**Ortak MediaPipe provider katmanı:**
```python
# core/liveness/mediapipe_provider.py
# Her detector bu provider'dan sonuç alır (tekrar yükleme yok)
# Singleton — model bir kez yüklenir

class MediaPipeProvider:
    NAME = "mediapipe_provider"

    def get(self, bgr_frame) -> FaceLandmarkerResult:
        # tasks API ile 478 landmark + blendshape
        ...

    def blink_score(self, result) -> tuple[float, float]:
        # sol/sağ göz blendshape skoru
        # eyeBlinkLeft, eyeBlinkRight → 0=açık, 1=kapalı

    def jaw_open_score(self, result) -> float:
        # jawOpen blendshape → 0=kapalı, 1=açık

    def head_yaw(self, result) -> float:
        # facial_transformation_matrix → yaw açısı (derece)
```

**Güçlendirilmiş modüller:**

| Modül | Mevcut sinyal | MediaPipe ile ek sinyal | Beklenen iyileştirme |
|---|---|---|---|
| `BlinkDetector` | EMA EAR dip (%15) | `eyeBlinkLeft/Right` blendshape | Iris normalize → kişiden bağımsız |
| `HeadMovementDetector` | Burun offset normalize | `facial_transformation_matrix` yaw | Kamera açısından tamamen bağımsız |
| `MouthMovementDetector` | Inner-lip MAR hysteresis | `jawOpen` blendshape | Sparse landmark hatasından kurtulur |

**Ensemble kararı:**
```python
# Her challenge için iki sinyal → weighted average
blink_score  = 0.4 * ear_dip + 0.6 * mediapipe_blink
head_score   = 0.3 * nose_offset + 0.7 * mp_yaw
mouth_score  = 0.4 * mar_hysteresis + 0.6 * mp_jaw_open
```

**Görev listesi:**
```
6.5.1  face_landmarker.task modelini indir
6.5.2  core/liveness/mediapipe_provider.py oluştur
6.5.3  BlinkDetector: blendshape ensemble ekle
6.5.4  HeadMovementDetector: transformation matrix yaw ekle
6.5.5  MouthMovementDetector: jawOpen ensemble ekle
6.5.6  Test: 3 modül ayrı ayrı webcam testi
6.5.7  Performans ölçümü: <500ms hedefi korunuyor mu?
```

**Risk:**
- MediaPipe 0.10.x `solutions` API yok → `tasks` API kullanılmalı
- `face_landmarker.task` ~30MB model dosyası — .gitignore'a eklenecek
- CPU overhead: MediaPipe + InsightFace birlikte ~400-500ms olabilir

---

### Sprint 6 — Yeni Liveness Modülleri

**Tarih:** 31.03.2026 – 25.04.2026 (26 gün)

#### MouthMovementDetector Planı

**Yöntem:** InsightFace `landmark_3d_68` — ağız landmark'ları

```
68-point model ağız indeksleri:
  Dış dudak: 48-59
  İç dudak:  60-67

MAR (Mouth Aspect Ratio):
  A = ||p51 - p59||  (dikey - üst-alt)
  B = ||p53 - p57||  (dikey - orta)
  C = ||p48 - p54||  (yatay)
  MAR = (A + B) / (2 * C)

  Ağız kapalı: MAR ≈ 0.3-0.5
  Ağız açık:   MAR > 0.6
```

**Challenge:** "Lütfen ağzınızı açın ve kapatın." (2 kez)
- Fotoğraf/ekran: MAR sabit kalır → FAIL
- Gerçek yüz: MAR dalgalanır → PASS

**Gereksinim:** Sadece `landmark_3d_68` — ekstra kurulum yok

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 6.1 | `MouthMovementDetector` implementasyonu (MAR, 68-point) | Yusuf | ✅ Tamamlandı |
| 6.2 | Test scripti + webcam doğrulama | Yusuf | ✅ Tamamlandı |
| 6.3 | Manager'a register + config güncelleme | Yusuf | ✅ Tamamlandı |

---

#### VoiceChallengeVerification Planı

**Mimari:**

```
Tarayıcı                    Backend
   │                           │
   ├─ getUserMedia(audio) ──►  │
   │  (MediaRecorder API)      │
   │                           │
   ├─ GET /voice/challenge ──► │ Rastgele kelime/sayı üret
   │  ◄── {text: "yedi üç"}   │ (örn: "yedi üç")
   │                           │
   │  Kullanıcı konuşur        │
   │                           │
   ├─ POST /voice/submit ────► │ Audio (WebM/OGG)
   │  {session_id, audio_b64} │
   │                           ├─ Whisper/SpeechRecognition
   │                           │   → transkript
   │                           │
   │  ◄── {passed, transcript} │ Karşılaştır
```

**Backend:**
- `pip install openai-whisper` (küçük model, CPU'da çalışır)
- Alternatif: `SpeechRecognition` + Google Web Speech API (internet gerektirir)
- Challenge: rastgele 2-3 rakam/kelime (Türkçe)

**Frontend:**
- `MediaRecorder API` ile ses kaydı (3 saniye)
- Base64 encode → backend'e gönder
- Ekranda "Söyleyin: yedi üç" göster

**Zorluklar:**
- Whisper kurulumu büyük (~150MB model)
- Türkçe tanıma için `whisper small` veya `medium` modeli
- Arka plan gürültüsü hassasiyeti

**Gereksinim:** `openai-whisper` veya `SpeechRecognition`

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 6.4 | `POST /voice/challenge` + `POST /voice/submit` endpoint | Mithatcan | 🔮 Ertelendi |
| 6.5 | Whisper/SpeechRecognition kurulumu + ses transkripsiyon | Yusuf | 🔮 Ertelendi |
| 6.6 | Frontend: MediaRecorder + ses kaydı bileşeni | İsmail | 🔮 Ertelendi |
| 6.7 | `VoiceChallenge.tsx` + verify akışına entegre | İsmail | 🔮 Ertelendi |

---

#### Öncelik Sırası

```
1. MouthMovementDetector  ← ÖNCE (sadece landmark, kolay)
2. VoiceChallengeVerification ← SONRA (ses altyapısı gerekli)
```

| # | Görev | Sorumlu | Durum |
|---|---|---|---|
| 6.8 | 3D maske saldırı simülasyonları | Yusuf | ⬜ Bekliyor |
| 6.9 | Performans darboğazı analizi | Mithatcan | ⬜ Bekliyor |

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
| 2026-05-20 | Sprint 4-5-6: E2E testler (14/14), performans ölçümleri, UI/UX redesign, güvenlik denetimleri, MouthMovementDetector, MiniFASNet denendi (ertelendi), README + API_CONTRACT dokümantasyonu | Claude Code |
