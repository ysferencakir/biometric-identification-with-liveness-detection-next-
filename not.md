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

//////////////////////////////////////////////////////////////////

scripts/live_recognition.py kodunu başarıyla güncelledim! Artık test ederken kamera görüntün (30 FPS) kesinlikle donmayacak ve akıcı kalacak. Arka planda saniyede atabildiği kadar API isteği atacak (varsayılan sınır max saniyede 15 kare --fps-cap 15 ile ayarlı). Arka plandan cevap geldikçe yüzünün etrafındaki kutunun konumu ve ismi canlı şekilde güncellenecektir.

Sorun 2: ONNX Runtime GPU'yu Gerçekten Kullanmıyor (Asıl Performans Sorunu)
Eğer 30 FPS akıcı görüntüden ziyade, "kutu takibi neden benimle eşzamanlı değil, biraz gecikmeli geliyor" dersen, bu tamamen modelin CPU'da çalışmasından dolayıdır.

Hatırlarsan sana Error 126'nın ONNX Runtime'ın CUDA DLL'lerini bulamaması olduğunu söylemiştim. Şu an sen Python kodunu her başlattığında sistemin Applied providers: ['CPUExecutionProvider'] diyor. CPU üzerinde ArcFace modeli kare başına 1.5 - 2 saniye arasında (yani ~0.5 FPS) sonuç döndürür. Bu, API'nin (Backend'in) her bir yüzü taraması için geçen ham süredir.

Kutunun senin hareketlerini saniyesi saniyesine (gerçek zamanlı) takip etmesi için GPU'yu aktif etmen şart.

GPU aktifleşirse bu süre yaklaşık 2 saniyeden -> 0.05 saniyeye (yani ~20-30 FPS) düşer.

Bu sorunu kökünden çözmek için:

Bilgisayarına CUDA Toolkit 12.1 veya 12.2 kur.
NVIDIA'nın sitesinden ona uygun cuDNN v8.9.x kur (Zip içerisindeki .dll dosyalarını CUDA klasörlerine kopyalıyorsun).
Bilgisayarı veya Terminali yeniden başlattığında, python main.py yazdığında o Error 126 gidecek ve terminalde şu mucizevi yazıyı göreceksin: Applied providers: ['CUDAExecutionProvider'].
O andan itibaren tanıma hızı muazzam seviyede artacak. Şimdilik benim yaptığım Threading düzenlemesi sayesinde kameran kasmayacak, kutu sadece yüzünü (CPU'nun hızına bağlı olarak) biraz arkadan takip edecektir. Şu an yeniden python scripts/live_recognition.py çalıştırıp akıcılığı test edebilirsin!