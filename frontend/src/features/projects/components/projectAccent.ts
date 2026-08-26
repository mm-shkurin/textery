import { documentTypeFromWire, type DocumentType } from '../../../shared/domain/documentTypes'
import projectsPageStyles from './ProjectsPage.module.css'

// Тип документа выбирает ОДНО имя акцента, а таблица цветов живёт в стилях: заливка бейджа,
// его текст и цвет папки двигаются вместе. Таблица, а не цепочка условий, потому что она
// исчерпывающая по DocumentType — новый тип без акцента станет ошибкой компиляции здесь,
// в файле, который обязан о нём знать.
// Прочитано с фрейма «Мои проекты — вид сетка — вариант 1 (Dekstop)»: эссе там коралловое,
// а не бирюзовое. Оно уехало бирюзовым и дало эссе и сочинению один бейдж и одну папку —
// ровно ту путаницу, ради которой тонировка и существует.
const ACCENT_BY_TYPE: Record<DocumentType, string> = {
  referat: 'blue',
  doklad: 'purple',
  sochinenie: 'teal',
  essay: 'coral',
}

/**
 * Класс акцента для типа с провода.
 *
 * Незнакомый тип всё равно получает карточку: синий — самый частый оттенок макета и наименее
 * неожиданный по умолчанию. Альтернатива — не вешать класс вовсе — нарисовала бы прозрачный
 * бейдж без заливки, что читается как сломанная карточка, а не как незнакомый тип.
 *
 * Общий для сетки и таблицы: два места, считающие цвет типа по-своему, — это два места, где
 * он разойдётся.
 */
export function accentClass(wireDocumentType: string): string {
  const appType = documentTypeFromWire(wireDocumentType)
  return projectsPageStyles[`project-card-accent-${appType ? ACCENT_BY_TYPE[appType] : 'blue'}`]
}
