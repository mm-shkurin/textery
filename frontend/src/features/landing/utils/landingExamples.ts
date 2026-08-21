import type { DocumentType } from '../../../shared/domain/documentTypes'

/**
 * The finished works shown on the landing under «Примеры готовых работ».
 *
 * Static copy, not a live feed of real documents, and deliberately so: every document in the
 * system belongs to the account that made it, and putting one on a public page would publish work
 * its author wrote for themselves. These four are written for this page and belong to nobody.
 *
 * The excerpt is what does the selling. A card that names four types and shows none of them asks
 * the visitor to take the product's word for the quality of its output on the one screen where
 * that is the only open question.
 */
export interface LandingExample {
  id: DocumentType
  title: string
  typeLabel: string
  volume: string
  // The opening of the work, as it would appear in the editor. Two or three sentences: enough to
  // show the register and the structure, short enough that the card stays a card.
  excerpt: string
}

export const LANDING_EXAMPLES: readonly LandingExample[] = [
  {
    id: 'referat',
    title: 'История развития космонавтики в XX веке',
    typeLabel: 'Реферат',
    volume: '8 страниц',
    excerpt:
      'Освоение космоса стало одним из определяющих научных сюжетов XX века. За шесть десятилетий ' +
      'человечество прошло путь от первых баллистических испытаний до постоянно обитаемых ' +
      'орбитальных станций. В работе рассматриваются ключевые этапы этого пути и решения, которые ' +
      'сделали каждый следующий шаг возможным.',
  },
  {
    id: 'doklad',
    title: 'Искусственный интеллект в современной медицине',
    typeLabel: 'Доклад',
    volume: '5 страниц',
    excerpt:
      'Сегодня алгоритмы машинного обучения читают снимки быстрее человека и не устают к концу ' +
      'смены. Но врач отвечает за диагноз, а алгоритм — нет, и именно здесь проходит граница их ' +
      'применения. Разберём, где ИИ уже приносит пользу, а где его выводы всё ещё требуют проверки.',
  },
  {
    id: 'essay',
    title: 'Свобода выбора в эпоху рекомендательных алгоритмов',
    typeLabel: 'Эссе',
    volume: '4 страницы',
    excerpt:
      'Мы привыкли считать выбор своим, если никто не держал нашу руку. Но лента, которая ' +
      'показывает одно и прячет другое, не принуждает — она сужает поле, в котором выбор вообще ' +
      'происходит. Свобода сегодня измеряется не количеством вариантов, а тем, кто их отобрал.',
  },
  {
    id: 'sochinenie',
    title: 'Природа как отражение внутреннего мира героя',
    typeLabel: 'Сочинение',
    volume: '3 страницы',
    excerpt:
      'Пейзаж в русской прозе редко бывает просто фоном. Гроза собирается тогда, когда герой ещё ' +
      'молчит; тишина над рекой наступает раньше, чем он находит нужные слова. Природа здесь ' +
      'говорит за человека то, в чём он сам себе пока не признался.',
  },
]
