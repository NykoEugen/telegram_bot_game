# JSON Configuration System

Цей документ описує нову систему конфігурації через JSON файли для описів нодів квестів, класів героїв та монстрів.

## Структура файлів

### 📁 data/
Папка містить всі JSON файли конфігурації:

- `hero_classes.json` - Класи героїв
- `monster_classes.json` - Класи монстрів  
- `quest_nodes.json` - Ноди квестів та їх зв'язки

## Класи героїв (hero_classes.json)

```json
{
  "hero_classes": [
    {
      "name": "Воїн",
      "description": "Міцний борець, який покладається на силу та витривалість.",
      "str_bonus": 2,
      "agi_bonus": 0,
      "int_bonus": 0,
      "vit_bonus": 2,
      "luk_bonus": 0,
      "stat_growth": {
        "str": 1,
        "agi": 0,
        "int": 0,
        "vit": 1,
        "luk": 0
      }
    }
  ]
}
```

### Поля:
- `name` - Назва класу
- `description` - Опис класу
- `*_bonus` - Стартові бонуси до характеристик
- `stat_growth` - Зростання характеристик за рівень

## Класи монстрів (monster_classes.json)

```json
{
  "monster_classes": [
    {
      "name": "Гоблін",
      "description": "Невеликий гуманоїдний монстр.",
      "monster_type": "humanoid",
      "difficulty": "easy",
      "base_str": 4,
      "base_agi": 7,
      "base_int": 3,
      "base_vit": 5,
      "base_luk": 6,
      "stat_growth": {
        "str": 0,
        "agi": 1,
        "int": 0,
        "vit": 0,
        "luk": 0
      }
    }
  ]
}
```

### Поля:
- `name` - Назва класу монстра
- `description` - Опис монстра
- `monster_type` - Тип монстра (humanoid, beast, undead, demon, elemental)
- `difficulty` - Складність (easy, normal, hard, boss)
- `base_*` - Базові характеристики
- `stat_growth` - Зростання характеристик за рівень

## Ноди квестів (quest_nodes.json)

```json
{
  "quests": [
    {
      "id": 2,
      "title": "The Dragon's Lair",
      "description": "A complex adventure with multiple paths...",
      "nodes": [
        {
          "id": "start",
          "type": "start",
          "title": "The Cave Entrance",
          "description": "You stand before a dark cave entrance...",
          "is_start": true,
          "is_final": false
        }
      ],
      "connections": [
        {
          "from": "start",
          "to": "left_tunnel",
          "type": "choice",
          "choice_text": "Take the illuminated tunnel",
          "order": 1
        }
      ]
    }
  ]
}
```

### Поля нодів:
- `id` - Унікальний ідентифікатор ноди
- `type` - Тип ноди (start, choice, action, end)
- `title` - Заголовок ноди
- `description` - Опис ноди
- `is_start` - Чи є початковою нодою
- `is_final` - Чи є фінальною нодою

### Поля з'єднань:
- `from` - ID ноди-джерела
- `to` - ID ноди-призначення
- `type` - Тип з'єднання (choice, default)
- `choice_text` - Текст вибору (для choice)
- `order` - Порядок вибору

## Використання в коді

### Завантаження класів героїв:
```python
from hero_system import HeroClasses

# Отримати всі класи
classes = HeroClasses.get_all_classes()

# Отримати клас за назвою
warrior = HeroClasses.get_class_by_name("Воїн")
```

### Завантаження класів монстрів:
```python
from monster_system import MonsterClasses

# Отримати всі класи
classes = MonsterClasses.get_all_classes()

# Отримати клас за назвою
goblin = MonsterClasses.get_class_by_name("Гоблін")
```

### Завантаження квестів:
```python
from quest_loader import QuestLoader

# Отримати всі квести
quests = QuestLoader.get_all_quests()

# Отримати квест за ID
quest = QuestLoader.get_quest_by_id(2)

# Отримати ноди квесту
nodes = QuestLoader.get_quest_nodes(2)

# Отримати з'єднання квесту
connections = QuestLoader.get_quest_connections(2)
```

## Ініціалізація

### Класи героїв:
```bash
python init_hero_classes.py
```

### Класи монстрів:
```bash
python init_monsters.py
```

### Квести:
```bash
python init_graph_quests.py
```

## Переваги JSON конфігурації

1. **Легкість редагування** - Не потрібно знати Python для зміни описів
2. **Відокремлення даних від коду** - Логіка та дані розділені
3. **Масштабованість** - Легко додавати нові класи та квести
4. **Валідація** - JSON можна перевіряти на валідність
5. **Версійний контроль** - Зміни в даних легко відстежувати

## Тестування

Для перевірки завантаження JSON файлів:

```bash
python test_json_loading.py
```

Цей скрипт перевіряє:
- Завантаження всіх класів героїв
- Завантаження всіх класів монстрів
- Завантаження всіх квестів та їх структури
