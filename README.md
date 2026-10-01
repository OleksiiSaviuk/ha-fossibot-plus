<div align="center">

# FOSSiBOT Power Station
### Home Assistant Custom Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Повноцінна інтеграція зарядних станцій FOSSiBOT у Home Assistant через хмарний API —
телеметрія у реальному часі та повне керування виходами і налаштуваннями.

</div>

---

## 🔌 Підтримувані пристрої

| Модель | Статус |
|--------|--------|
| FOSSiBOT F1800 Pro | ✅ Протестовано |
| Інші моделі Fossibot+ | ⚠️ Можливо сумісні |

> Підтримує декілька станцій в одному обліковому записі — кожна отримає окремий пристрій із серійним номером у назві (наприклад `Fossibot-F180V012605B4936`).

---

## ✨ Сутності

### 📊 Сенсори

| Назва | Одиниці | Опис |
|-------|---------|------|
| **Battery** | % | Рівень заряду акумулятора |
| **Temperature** | °C | Температура станції |
| **Time remaining** | хв | Час до повного заряду або розряду |
| **Charging** | — | Активне заряджання (1=так, 0=ні) |
| **Output power** | W | Поточна вихідна потужність |
| **AC output voltage** | V | Напруга на виході AC (~230 В) |
| **AC frequency** | Hz | Частота вихідного змінного струму |
| **AC grid power** | W | Потужність від мережі змінного струму |
| **Total input power** | W | Сумарна вхідна потужність (мережа AC + сонце) |
| **Charge power** | W | Загальна потужність заряджання |

### 🎛️ Перемикачі

| Назва | Опис |
|-------|------|
| **AC output** | Вмикання/вимикання розеток змінного струму |
| **DC output** | Вмикання/вимикання виходу постійного струму 12V |
| **USB output** | Вмикання/вимикання USB-портів |
| **Sound** | Вмикання/вимикання звукових сповіщень |
| **Output memory** | Пам'ять стану виходів після відновлення живлення |

### 🔽 Дропдауни (Select)

| Назва | Опції | Опис |
|-------|-------|------|
| **LED mode** | Off / Steady / SOS / Strobe | Режим вбудованого світлодіода |
| **Charge mode** | UPS / ECO | Режим зарядки від мережі |

---

## 🚀 Встановлення

### Через HACS (рекомендовано)

1. Відкрийте **HACS** → натисніть ⋮ → **Custom repositories**
2. Додайте `https://github.com/zelin-sky/ha-fossibot-plus` → категорія **Integration**
3. Знайдіть **FOSSiBOT Power Station** → натисніть **Download**
4. Перезапустіть Home Assistant

### Вручну

1. Скопіюйте `custom_components/fossibot_plus/` до `<config>/custom_components/`
2. Перезапустіть Home Assistant

### Налаштування

1. **Налаштування** → **Пристрої та служби** → **Додати інтеграцію** → **FOSSiBOT Power Station**
2. Введіть email та пароль від застосунку **Fossibot+**

---

## 📡 Технічні деталі

### Архітектура

```
Fossibot+ Cloud (app.fossibot.hk)
        │
        ├── POST /prod-api/app/user/login           →  JWT токен
        ├── GET  /prod-api/app/user_device/list     →  Список пристроїв + стан online
        ├── GET  /prod-api/app/ctrl/route?cmd=...   →  Команди керування
        └── WS   ws://app.fossibot.hk/ws            →  Телеметрія (~1 кадр/сек)
```

### Протокол телеметрії (TLV)

Сервер надсилає бінарні кадри через WebSocket приблизно раз на секунду.

```
[6 байт header][N × (2 байти тег + 4 байти значення LE)][2 байти CRC16/MODBUS]
```

### Підтверджені теги

| Тег | Назва | Scale | Опис |
|-----|-------|-------|------|
| `0100` | Battery | ×1 | SOC (%) |
| `0200` | Temperature | low16, ×1 | Температура (°C)¹ |
| `0300` | Time remaining | ×1 | Залишок часу (хв) |
| `0400` | Charging | — | Активне заряджання (0/1) |
| `1300` | AC grid power | ×1 | Вхідна потужність від мережі (W) |
| `1400` | Output power | ×1 | Вихідна потужність (W) |
| `1500` | AC output voltage | ×0.1 | Вихідна напруга AC (V) |
| `1600` | AC frequency | ×0.1 | Частота AC (Hz) |
| `2200` | Total input power | ×1 | Сумарна вхідна потужність (W) |
| `2600` | LED mode | — | 0=вимк, 1=постійний, 2=SOS, 3=строб |
| `2700` | AC output | — | AC вихід (0/1) |
| `2800` | DC output | — | DC вихід (0/1) |
| `2900` | USB output | — | USB вихід (0/1) |
| `2a00` | Charge power | ×1 | Потужність заряджання (W) |
| `2b00` | Output memory | — | Пам'ять виходів (0/1) |
| `2c00` | Screen timeout | — | 0=завжди, 1=30с, 2=1хв, 3=5хв, 4=10хв, 5=30хв |
| `2d00` | Power-off timer | — | 0=ніколи, 1=5хв, 2=10хв, 3=1г, 4=8г |
| `2e00` | Charge mode | — | 0=UPS, 1=ECO |
| `3300` | Sound | — | Звук (0/1) |

> ¹ Деякі моделі пакують метадані у старші 16 біт тегу `0200`. Інтеграція автоматично бере лише молодші 16 біт, що коректно для всіх відомих моделей.

### Формат команди керування

```
cmd = "0e000c000800" + tag(2B LE) + value(4B LE) + CRC16/MODBUS(tag+value, BE)
GET /prod-api/app/ctrl/route?snCode=<SN>&cmd=<cmd>
```

CRC підтверджено для всіх перехоплених команд (AC/DC/USB/LED/Sound/Memory/Mode).

### Надійність

| Механізм | Деталі |
|----------|--------|
| **Heartbeat** | `{"type":"hear","msg":"email"}` кожні 5 с |
| **Watchdog** | Якщо WS мовчить >30 с — перепідключення |
| **Anti-dup guard** | Ретрай через 6 с при помилці `重复提交` |
| **Token refresh** | Автоматичний перелогін при `401` |
| **Online polling** | REST-перевірка стану кожну хвилину |

---

## 🐛 Debug logging

```yaml
logger:
  default: warning
  logs:
    custom_components.fossibot_plus: debug
```

---

## 🤝 Внесок

Особливо корисним буде:
- Charles-захоплення нових команд
- Логи при різних станах для підтвердження невідомих тегів
- Тестування на інших моделях FOSSiBOT

---

<div align="center">
Зроблено з ❤️. Зроблено в Україні
</div>
