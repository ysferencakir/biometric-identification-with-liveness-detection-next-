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

