# Yuklama testi (load test)

12-bo'lim talabiga ko'ra release oldidan yuklama testi o'tkaziladi.

## O'rnatish

```bash
pip install locust
```

## Ishga tushirish

```bash
# Faqat public yo'llar (health/openapi)
locust -f loadtest/locustfile.py --host http://localhost:8000

# Autentifikatsiyalangan yo'llar bilan
KIDSFLOW_LOGIN=+998901112233 KIDSFLOW_PASSWORD=parol1234 \
  locust -f loadtest/locustfile.py --host http://localhost:8000
```

So'ng http://localhost:8089 ni oching, foydalanuvchilar soni va spawn rate'ni belgilang.

## Headless (CI/skript) rejimi

```bash
locust -f loadtest/locustfile.py --host http://localhost:8000 \
  --headless -u 50 -r 5 -t 2m --csv=loadtest/report
```

- `-u 50` — 50 ta parallel foydalanuvchi
- `-r 5` — sekundiga 5 tadan qo'shish
- `-t 2m` — 2 daqiqa davomida
- `--csv` — natijalarni CSV'ga yozadi

## E'tibor bering

- Login endpointida rate limit bor (`LOGIN_RATE_LIMIT_MAX`). Yuklama testida
  ko'p login urinishlari 429 qaytishi mumkin — bu kutilgan xatti-harakat.
- Yuklama testini **staging** muhitida o'tkazing, production'da emas.
