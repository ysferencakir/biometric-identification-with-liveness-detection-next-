# 🧪 İlk Çalıştırma Test Planı

> **Proje:** Biometric Identification – Face Recognition Module  
> **Test ortamı:** Windows 11 · PowerShell · Python 3.10+ · RTX 4070

---

## Faz 0 – Ortam Kurulumu (bir kez)

```powershell
# 1. Backend klasörüne geç
cd C:\Users\mitha\Desktop\Projeler\Grad\backend

# 2. Sanal ortam oluştur ve aktifleştir
python -m venv .venv
.venv\Scripts\activate

# 3. Build toolları (insightface cmake gerektirir; sisteme kurulu değilse)
pip install cmake

# 4. Temel paketleri yükle
pip install -r requirements.txt

# 5. GPU ONNX Runtime kur (RTX 4070 – CUDA 12.x)
pip install onnxruntime-gpu==1.18.0

# 6. GPU provider doğrula
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
# Beklenen: ['CUDAExecutionProvider', 'CPUExecutionProvider']

# 7. .env oluştur
copy .env.example .env
```

> [!IMPORTANT]
> `onnxruntime` ve `onnxruntime-gpu` aynı anda kurulmamalı.  
> Eğer önceden `onnxruntime` kuruluysa: `pip uninstall onnxruntime`

---

## Faz 1 – Backend Başlatma Testi

```powershell
# Backend klasöründe, .venv aktifken:
python main.py
```

### ✅ Beklenen Çıktı (sırasıyla)
```
INFO | __main__ | === Biometric ID API starting up ===
INFO | db.store | Database initialised at data/biometric.db
INFO | __main__ | Loading InsightFace model – please wait…
INFO | core.detection | InsightFace loaded on GPU (ctx_id=0)
INFO | __main__ | InsightFace model ready ✓
INFO | __main__ | === API ready at http://0.0.0.0:8000 ===
```

> [!NOTE]
> İlk başlatmada InsightFace **buffalo_l** modelini (~500 MB) internetten indirir.  
> `~/.insightface/models/buffalo_l/` altına kaydeder. Sonraki başlatmalarda anlıktır.

---

## Faz 2 – API Endpoint Testleri

Backend çalışırken **yeni bir PowerShell terminali** aç.

### Test 1 – Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -Method GET
```
**Beklenen:**
```json
{ "status": "ok", "version": "0.1.0", "model": "buffalo_l" }
```

---

### Test 2 – Kullanıcı Listesi (boş DB)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users" -Method GET
```
**Beklenen:**
```json
{ "users": [], "count": 0 }
```

---

### Test 3 – Swagger UI Doğrulama
Tarayıcıda aç: **http://localhost:8000/docs**

Görünmesi gereken endpointler:
- `GET /api/v1/health`
- `POST /api/v1/recognize`
- `POST /api/v1/recognize/upload`
- `POST /api/v1/register`
- `GET /api/v1/users`
- `DELETE /api/v1/users/{user_id}`

---

### Test 4 – Boş Frame Gönderimi (edge case)
```powershell
$body = @{ image_b64 = "invalidbase64!!" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/recognize" `
  -Method POST -Body $body -ContentType "application/json"
```
**Beklenen:** HTTP 400 + `"Cannot decode image..."` mesajı

---

### Test 5 – Gerçek Yüz Olmadan Tanıma (yüz yok)
```powershell
# Siyah 1x1 piksel PNG → base64
$body = @{
  image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/recognize" `
  -Method POST -Body $body -ContentType "application/json"
```
**Beklenen:**
```json
{ "face_detected": false, "face_count": 0, "recognized": false, "message": "No face detected" }
```

---

## Faz 3 – Kullanıcı Kayıt Testi

```powershell
# Backend çalışırken, backend klasöründen:
python scripts/register_user.py --name "Mithat" --auto
```

### Kayıt Akışı
1. Kamera açılır
2. Yüzünü çerçeveye koy → "Face OK" yeşil görünmeli
3. Auto mode: 1 frame/sn otomatik çeker
4. 7 frame tamamlanınca kamera kapanır
5. Backend'e gönderilir

### ✅ Beklenen Terminal Çıktısı
```
[INFO] Registering user: Mithat
[INFO] Target frames  : 7
[INFO] Auto-capture   : True
[INFO] Captured 1/7
...
[INFO] Captured 7/7
[INFO] Sending 7 frames to http://localhost:8000/api/v1/register…

✅ Registration successful!
   Name      : Mithat
   User ID   : xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Frames used: 7
```

### Kayıt Sonrası Doğrulama
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users" -Method GET
```
**Beklenen:** `count: 1`, kullanıcı adı "Mithat"

---

## Faz 4 – Gerçek Zamanlı Tanıma Testi

```powershell
python scripts/live_recognition.py
```

### Beklenen Davranışlar

| Durum | Görsel |
|-------|--------|
| Kameranın önünde değilsin | Kutu yok, "No face detected" |
| Yüzün görünüyor, kayıtlı | 🟢 Yeşil kutu + "Mithat (0.87)" |
| Yüzün görünüyor, kayıtsız | 🔴 Kırmızı kutu + "Unknown (0.32)" |
| İki kişi aynı anda | Kutu yok, "Multiple faces detected" |

**Q** tuşuna bas → kapanır.

---

## Faz 5 – Kullanıcı Silme Testi

```powershell
# Önce user_id'yi al
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users" -Method GET
$id = $users.users[0].id

# Sil
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/$id" -Method DELETE
```
**Beklenen:** `{ "success": true, "message": "User '...' deleted" }`

---

## Faz 6 – GPU Doğrulama

Backend loglarında şunu ara:
```
InsightFace loaded on GPU (ctx_id=0)
```

Eğer `CPU (fallback)` görünüyorsa:
```powershell
# CUDA provider kontrolü
python -c "
import onnxruntime as ort
print('Providers:', ort.get_available_providers())
print('GPU available:', 'CUDAExecutionProvider' in ort.get_available_providers())
"
```

---

## Bilinen Olası Hatalar & Çözümleri

| Hata | Neden | Çözüm |
|------|-------|-------|
| `No module named 'insightface'` | pip install yapılmadı | `pip install insightface==0.7.3` |
| `cmake not found` | Build tools eksik | `pip install cmake` veya VS Build Tools |
| `CUDAExecutionProvider not in providers` | onnxruntime-gpu yok/yanlış | `pip install onnxruntime-gpu==1.18.0` |
| `Cannot open camera 0` | Kamera başka uygulama kullanıyor | Tarayıcı kamera izni kapat; `--cam 1` dene |
| `OSError: [WinError 10061] Connection refused` | Backend çalışmıyor | `python main.py` ile başlat |
| `HTTP 422` kayıtta | 3'ten az geçerli frame | Daha iyi ışık, tek yüz, kameraya yakın dur |
| `buffalo_l` model indirme başarısız | İnternet/firewall | VPN kapat; `~/.insightface/models/` klasörünü kontrol et |

---

## Hızlı Referans Komutları

```powershell
# Backend başlat
python main.py

# Kullanıcı kaydet (auto mode)
python scripts/register_user.py --name "AdSoyad" --auto

# Kullanıcı kaydet (manuel SPACE)
python scripts/register_user.py --name "AdSoyad"

# Gerçek zamanlı tanıma
python scripts/live_recognition.py

# Tüm kullanıcıları listele
Invoke-RestMethod http://localhost:8000/api/v1/users

# Swagger UI
start http://localhost:8000/docs
```
