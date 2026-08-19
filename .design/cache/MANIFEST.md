# Кэш дизайна — карта фреймов

Файл Figma: `rA86oLSfshnx9CYlAtSfqr`, страница `Textery`, секция `светлая тема`.
Сырой `file.json` (48 МБ) и `imagefills.json` в git не хранятся — они восстанавливаются
одним запросом `.design/fetch-figma.sh`. В репозитории лежат обрезанные поддеревья.

| slug (`.design/cache/nodes/<slug>.json`) | node id | фрейм в Figma |
|---|---|---|
| `landing-desktop` | `90:880` | Desktop — главная страница |
| `navbar-variant5` | `1086:4929` | Navbar/Variant5 — авторизованный пользователь |
| `create-project` | `788:5094` | Мои проекты - Создать проект |
| `create-project-mobile` | `1227:9974` | Mobile рядом с ним |
| `cards-images` | `788:6243` | Cards/Images color folders (8 вариантов: Referat, Resume, Doklad, Sochinenia, Essay, Buisness plan, Summary, Letter) |
| `projects-grid` | `484:1104` | Мои проекты - вид сетка - вариант 1 (Dekstop) |
| `projects-grid-mobile` | `674:2534` | Mobile рядом с ним |
| `profile-personal` | `1127:10768` | Профиль - личные данные (базовое состояние) |
| `profile-mobile` | `1311:7203` | Mobile к базовому |
| `profile-edit-name` | `1202:6364` | Профиль — редактирование имени (по клику «Изменить» появляется поле, курсор сразу внутри) |
| `profile-edit-name-mobile` | `1311:11006` | Mobile к нему |
| `profile-save` | `1227:9790` | Профиль — сохранение изменений (alert при смене имени и после загрузки/удаления фото) |
| `profile-save-mobile` | `1311:11272` | Mobile к нему |
| `profile-delete` | `1202:6227` | Профиль — удаление аккаунта |
| `profile-delete-mobile` | `1311:11406` | Mobile к нему |

## Ассеты (`.design/cache/assets/`)

- `icon-*.svg` — 37 иконок из `UI Kit 2/Icons/Set 24px` (all, referat, book, hat, books,
  essay, text, search, arrow-*, grid, list, filter, cross, sort, rename, dublicate, delete,
  logout, settings, card, attach, home, cloud-no, cloud-yes, plus, profile, infinity,
  thunder, export, stars, personal, renewal, payment).
- `file-*.svg` — 7 иконок типов файлов из `UI Kit 2/Icons/Files`.
- **`card-*.png` отсутствуют.** Экспорт восьми картинок `Cards/Images color folders`
  упёрся в **429** и был прерван без ретрая. Их id уже лежат в `.design/export-ids.txt`
  (строки с `png`). Добрать позже **одним** запросом, когда лимит остынет:
  `set -a; . ./infra/.env; set +a; bash .design/fetch-figma.sh`
  (svg-часть перескочит по кэшу, останется единственный png-вызов).

## Токены

`.design/cache/tokens.json` — 48 цветов, 40 текстовых стилей, радиусы, тени, gap'ы и
паддинги с частотой употребления. Базовая типографика — **Inter**, ключевой акцент —
`#004EE0`, серый текст — `#6B7280` / `#464551`, тёмный — `#1F1F1F`.
