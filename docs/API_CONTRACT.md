
# API Sözleşmesi

> **Versiyon:** 0.2
> **Base URL:** `http://localhost:8000/api/v1`
> **Son Güncelleme:** 2026-05-19

Bu doküman frontend ↔ backend arasındaki tüm endpoint sözleşmelerini tanımlar.
Tüm istek gövdeleri JSON, tüm yanıtlar JSON'dır. Görsel akış için bkz. `GELISTIRME_PLANI.md`.

---

## İçindekiler

1. [Mevcut Endpoint'ler (v0.1)](#mevcut-endpointler-v01)
2. [Yeni Endpoint'ler (v0.2 — Session & Liveness)](#yeni-endpointler-v02)
3. [Hata Formatı](#hata-formatı)
4. [Durum Kodları](#durum-kodları)

---

## Mevcut Endpoint'ler (v0.1)

### `GET /health`

Sistem sağlık kontrolü.

**Yanıt `200`**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "model": "buffalo_l"
}
```

---

### `POST /register`

Yeni kullanıcı kaydı. Birden fazla kamera karesi gerektirir.

**İstek**
```json
{
  "name": "Yusuf Eren",
  "frames": ["<base64>", "<base64>", "<base64>"]
}
```

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| `name` | string | ✅ | Kullanıcı adı (1-128 karakter) |
| `frames` | string[] | ✅ | Base64 JPEG/PNG listesi, min 3 |

**Yanıt `200`**
```json
{
  "success": true,
  "user_id": "uuid-xxxx",
  "name": "Yusuf Eren",
  "frames_used": 4,
  "message": "User registered successfully"
}
```

---

### `POST /recognize`

Base64 frame ile yüz tanıma.

**İstek**
```json
{
  "image_b64": "<base64>",
  "threshold": 0.5
}
```

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| `image_b64` | string | ✅ | Base64 JPEG/PNG |
| `threshold` | float | ❌ | Cosine similarity eşiği (0-1), varsayılan config'den |

**Yanıt `200`**
```json
{
  "face_detected": true,
  "face_count": 1,
  "recognized": true,
  "user_id": "uuid-xxxx",
  "name": "Yusuf Eren",
  "recognition_score": 0.87,
  "bbox": [120, 80, 200, 240],
  "message": "Recognized"
}
```

---

### `POST /recognize/upload`

Multipart file upload ile yüz tanıma.

**İstek** — `multipart/form-data`

| Alan | Tip | Zorunlu |
|---|---|---|
| `file` | File (JPEG/PNG) | ✅ |
| `threshold` | float | ❌ |

**Yanıt** — `RecognitionResponse` (yukarıdaki ile aynı)

---

### `GET /users`

Kayıtlı kullanıcı listesi.

**Yanıt `200`**
```json
{
  "users": [
    { "id": "uuid-xxxx", "name": "Yusuf Eren", "created_at": "2025-10-01T..." }
  ],
  "count": 1
}
```

---

### `DELETE /users/{user_id}`

Kullanıcı sil.

**Yanıt `200`**
```json
{ "success": true, "message": "User 'uuid-xxxx' deleted" }
```

**Yanıt `404`** — Kullanıcı bulunamadı.

---

## Yeni Endpoint'ler (v0.2)

> Bu endpoint'ler Sprint 2'de (Mithatcan) implemente edilecek.

### `GET /liveness/available`

Sistemde kayıtlı liveness modüllerini listele.

**Yanıt `200`**
```json
{
  "detectors": [
    {
      "name": "blink",
      "instruction": "Lütfen iki kez göz kırpın."
    },
    {
      "name": "head_movement",
      "instruction": "Başınızı yavaşça sağa çevirin."
    },
    {
      "name": "texture",
      "instruction": "Kameraya düz bakın."
    }
  ]
}
```

---

### `POST /session/create`

Yeni doğrulama oturumu başlat. Backend **rastgele 2** liveness modülü seçer.

**İstek** — Gövde gerekmez.

**Yanıt `200`**
```json
{
  "session_id": "uuid-yyyy",
  "challenges": ["blink", "texture"],
  "expires_at": "2025-10-01T12:05:00Z"
}
```

| Alan | Açıklama |
|---|---|
| `session_id` | Sonraki tüm isteklerde kullanılır |
| `challenges` | Sırayla tamamlanacak 2 modülün NAME'i |
| `expires_at` | Session TTL (varsayılan 5 dakika) |

---

### `GET /session/{session_id}`

Session durumunu sorgula.

**Yanıt `200`**
```json
{
  "session_id": "uuid-yyyy",
  "status": "active",
  "challenges": ["blink", "texture"],
  "completed_challenges": ["blink"],
  "expires_at": "2025-10-01T12:05:00Z"
}
```

| `status` değerleri | Anlam |
|---|---|
| `active` | Session sürüyor |
| `completed` | Her iki liveness geçildi, verify bekliyor |
| `expired` | TTL doldu |
| `denied` | Liveness başarısız, erişim reddedildi |

---

### `POST /liveness/submit`

Bir liveness challenge için frame gönder.

**İstek**
```json
{
  "session_id": "uuid-yyyy",
  "challenge_name": "blink",
  "frame": "<base64>"
}
```

| Alan | Tip | Zorunlu | Açıklama |
|---|---|---|---|
| `session_id` | string | ✅ | Aktif session UUID |
| `challenge_name` | string | ✅ | Tamamlanmak istenen modülün NAME'i |
| `frame` | string | ✅ | Base64 JPEG/PNG |

**Yanıt `200`**
```json
{
  "challenge_name": "blink",
  "passed": true,
  "confidence": 0.91,
  "instruction": "Lütfen iki kez göz kırpın.",
  "all_challenges_passed": false
}
```

| Alan | Açıklama |
|---|---|
| `passed` | Bu challenge geçildi mi |
| `confidence` | Modelin güven skoru (0-1) |
| `instruction` | Kullanıcıya gösterilecek sonraki talimat (başarısızsa tekrar dene) |
| `all_challenges_passed` | `true` ise `/verify` çağrısına geç |

**Hata `400`** — Session süresi dolmuş veya geçersiz challenge name.
**Hata `409`** — Challenge zaten tamamlanmış.

---

### `POST /verify`

Her iki liveness tamamlandıktan sonra biyometrik doğrulama yap.

**İstek**
```json
{
  "session_id": "uuid-yyyy",
  "frame": "<base64>"
}
```

| Alan | Tip | Zorunlu |
|---|---|---|
| `session_id` | string | ✅ |
| `frame` | string | ✅ |

**Yanıt `200`**
```json
{
  "access_granted": true,
  "matched_user": "uuid-xxxx",
  "name": "Yusuf Eren",
  "recognition_score": 0.89,
  "liveness_results": [
    { "challenge": "blink",   "passed": true, "confidence": 0.91 },
    { "challenge": "texture", "passed": true, "confidence": 0.84 }
  ],
  "decision_reason": "Recognised"
}
```

**Yanıt `200` (reddedildi)**
```json
{
  "access_granted": false,
  "matched_user": null,
  "name": null,
  "recognition_score": 0.0,
  "liveness_results": [...],
  "decision_reason": "Face not recognised"
}
```

`decision_reason` değerleri:

| Değer | Anlam |
|---|---|
| `"Recognised"` | Erişim verildi |
| `"Face not recognised"` | Yüz DB'de yok |
| `"No face detected"` | Frame'de yüz yok |
| `"Multiple faces"` | Birden fazla yüz |
| `"Liveness failed"` | Liveness challenge geçilemedi |
| `"Low liveness confidence"` | Ortalama güven < 0.7 |
| `"Session expired"` | Session süresi dolmuş |
| `"Challenges not completed"` | Liveness tamamlanmadan verify çağrıldı |

**Hata `400`** — Session geçersiz veya liveness tamamlanmamış.

---

## Hata Formatı

Tüm hatalar şu formatta döner:

```json
{
  "detail": "Açıklayıcı hata mesajı"
}
```

---

## Durum Kodları

| Kod | Anlam |
|---|---|
| `200` | Başarılı |
| `400` | Geçersiz istek (hatalı format, süresi dolmuş session) |
| `404` | Kaynak bulunamadı |
| `409` | Çakışma (zaten tamamlanmış) |
| `422` | Doğrulama hatası (Pydantic) |
| `500` | Sunucu hatası |
