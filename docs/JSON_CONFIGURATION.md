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
      "requires": {
        "quests_completed": [1],
        "rep": {
          "mages_guild": 15
        }
      },
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
- `world_flags` - Дії над світовими прапорцями (`set`, `clear`)
- `events` - Список подій, що відбуваються при вході в ноду

### Поля з'єднань:
- `from` - ID ноди-джерела
- `to` - ID ноди-призначення
- `type` - Тип з'єднання (choice, default)
- `choice_text` - Текст вибору (для choice)
- `order` - Порядок вибору
- `conditions` - Умови переходу (наприклад, `world_flags.has`, `world_flags.missing`)
- `effects` - Наслідки переходу (`world_flags.set`, `world_flags.clear`)

### Вимоги квесту (`requires`):
- `quests_completed` - список ID квестів, які необхідно завершити до старту
- `rep` - словник з кодами фракцій та мінімальними значеннями репутації
- `world_flags` - очікувані значення прапорців світу (`has`, `missing`)

## Події у вузлах (`events`)

Події дозволяють додати пастки, загадки, перевірки характеристик та story moments. Кожен елемент списку має структуру:

```json
{
  "id": "rune_flare_trap",
  "type": "stat_check",
  "attribute": "agi",
  "difficulty": 12,
  "success": {
    "text": "Ви спритно ковзаєте між рунами.",
    "reward": {
      "world_flags": {"set": {"moonwell.haste_bonus": true}}
    }
  },
  "failure": {
    "text": "Рунічне полум'я обпікає вас (-8 HP).",
    "damage": 8
  }
}
```

Підтримувані типи:

- `stat_check` / `trap` — перевірка атрибуту героя (`str`, `agi`, `int`). Параметри: `attribute`, `difficulty`, опціонально `dice` (наприклад, `6` для d6). Гілки `success` та `failure` можуть містити `text`, `damage`, `require_recovery`, `reward`.
- `puzzle` — flavour-подія з автоматичним успіхом. Використовуйте `text` та `reward`.
- `story_moment` — рідкісний момент історії з унікальними нагородами. Поля: `text`, `story_key` (необов'язково), `reward`.

Поля `reward` підтримують:

- `items` — список `{ "code": "item_code", "quantity": 1 }`
- `world_flags` — дії над прапорцями (`set`, `clear`)
- `metric` або `metrics` — оновлення прогресу (наприклад, `story_moments`)

Результати подій зберігаються у стані квесту, тому однаковий event не повторюється, якщо `repeatable` не встановлено в `true`.

## Ланцюги квестів (`chain`)

Кожен квест може належати до ланцюга та зберігати прогрес у профілі героя.

```json
{
  "chain": {
    "id": "moonwell_recovery",
    "step": 2
  }
}
```

- `id` — унікальний ідентифікатор ланцюга
- `step` — номер кроку в межах ланцюга; під час завершення квесту цей крок записується у прапорець `<id>.step`
- Разом із `world_flags` у нодах/зв'язках дозволяє будувати альтернативні фінали та наступні етапи історії

## Світові прапорці (`world_flags`)

Світові прапорці — це ключі та значення, що зберігаються в герої та впливають на доступні гілки, діалоги й квести.

- У нодах: `world_flags.set` / `world_flags.clear` застосовуються, коли герой входить у ноду
- У з'єднаннях: `conditions.world_flags` перевіряє наявність/відсутність прапорців, `effects.world_flags` змінює їх при переході
- У `requires.world_flags` — задають глобальні умови старту квесту

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
