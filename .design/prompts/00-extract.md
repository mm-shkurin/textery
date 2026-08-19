# Сессия 0 — извлечение дизайна из Figma (запускать ПЕРВОЙ, одну, ни с кем параллельно)

Ты единственная сессия, которой разрешено обращаться к Figma API. Все остальные
сессии работают офлайн по кэшу, который ты создашь.

## Жёсткие ограничения
- Прочитай `.design/README.md` целиком до первой команды.
- Бюджет запросов: 1 × `GET /v1/files/:key`, 1 × `/v1/files/:key/images`,
  максимум 3 × `/v1/images/:key?ids=...` (id батчами через запятую).
- **429 = стоп.** Не повторять запрос, не делать retry-цикл, не ходить по нодам
  поштучно. Повторные 429 блокируют токен на 36 часов.
- Токен берёшь из `infra/.env` (`FIGMA_TOKEN`). В репозиторий его не писать.

## Что сделать
1. `FIGMA_TOKEN=... FIGMA_FILE_KEY=... bash .design/fetch-figma.sh` — получишь
   `.design/cache/file.json`.
2. Дальше **офлайн**, скриптами по `file.json`, найди по имени и выпиши node id:
   | slug | имя фрейма в Figma |
   |------|--------------------|
   | `landing-desktop`  | Desktop (главная страница) |
   | `navbar-variant5`  | Navbar/Variant5 (авторизованный пользователь) |
   | `create-project`   | Мои проекты - Создать проект |
   | `create-project-mobile` | Mobile рядом с «Создать проект» |
   | `cards-images`     | Cards/Images color folders (картинки типов генерации) |
   | `projects-grid`    | Мои проекты - вид сетка - вариант 1 (Dekstop) |
   | `profile-personal` | Профиль - личные данные |
   | `profile-mobile`   | Mobile рядом с «Профиль - личные данные» |
3. Для каждого slug выпиши обрезанное поддерево в `.design/cache/nodes/<slug>.json`:
   оставь только `name, type, absoluteBoundingBox, layoutMode, itemSpacing, padding*,
   primaryAxisAlignItems, counterAxisAlignItems, layoutSizing*, constraints, fills,
   strokes, strokeWeight, cornerRadius, effects, style (шрифт/размер/межстрочный/вес/
   letterSpacing), characters, opacity, children`. Всё остальное выкинуть — иначе
   файлы неподъёмные.
4. Собери `.design/cache/tokens.json`: все уникальные цвета (hex + где встречается),
   типографическую шкалу, радиусы, тени, шаги отступов. Сравни с
   `frontend/src/styles` / `index.css` и отметь, какие токены в коде уже есть,
   а каких не хватает.
5. Составь `.design/export-ids.txt` (`<nodeid> <slug> <svg|png>`) для всех иконок,
   иллюстраций и картинок типов генерации из `Cards/Images color folders`,
   затем **один раз** перезапусти `fetch-figma.sh` — он добьёт экспорт батчем.
   Иконки — `svg`, растровые иллюстрации — `png@2x`.
6. Напиши `.design/cache/MANIFEST.md`: фрейм → node id → slug → список ассетов →
   какие файлы фронтенда, вероятно, соответствуют (по `frontend/src/features/*`).
7. Коммит: `design: figma cache and extracted design tokens`.

## Условие завершения
Сессии 1–4 должны суметь сделать всю работу, ни разу не зайдя в сеть. Если чего-то
не хватает — они сообщат node id, ты добавишь их одним батчем.
