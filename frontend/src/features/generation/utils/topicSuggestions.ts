import type { DocumentType } from '../../../shared/documentTypes'

/**
 * «Увидеть примеры запросов» — the prompts offered under the topic field.
 *
 * Per type, not one shared list: a topic that makes a good реферат («История развития
 * космонавтики») makes a poor сочинение, and a single list would show three quarters of its
 * suggestions to the wrong screen. The examples are what the field is FOR, shown to a visitor who
 * has an assignment in mind but not a sentence — which is the state the empty composer leaves
 * them in.
 *
 * Three each, deliberately: they sit above the fold beside a textarea, and a fourth row pushes the
 * «Сгенерировать» button off a laptop screen.
 */
export const TOPIC_SUGGESTIONS: Record<DocumentType, readonly string[]> = {
  doklad: [
    'Искусственный интеллект в современной медицине',
    'Освоение Арктики: история и перспективы',
    'Возобновляемая энергетика в России',
  ],
  referat: [
    'История развития космонавтики в XX веке',
    'Экономические причины Великой депрессии',
    'Роль микропластика в загрязнении океана',
  ],
  essay: [
    'Можно ли доверять решениям искусственного интеллекта',
    'Свобода выбора в эпоху рекомендательных алгоритмов',
    'Нужны ли человеку бумажные книги',
  ],
  sochinenie: [
    'Что значит быть честным перед самим собой',
    'Природа как отражение внутреннего мира героя',
    'Почему добро требует смелости',
  ],
}

/** The suggestions for a type, or an empty list for a type this table has never heard of. */
export function suggestionsFor(documentType: DocumentType): readonly string[] {
  return TOPIC_SUGGESTIONS[documentType] ?? []
}
