import landingSectionStyles from './LandingSection.module.css'
import styles from './LandingFaq.module.css'

// Figma `Desktop` → `FAQ` (node 1097:12035): six white cards at a 12px radius in TWO columns, each
// with a `+` at its right edge that becomes a `×` once the card is open.
//
// Both the questions and the answers are the frame's expanded state, with two numbers corrected to
// the ones the comparison table above states: the frame's answer says «28 сек» and «68–85%» while
// the table says 30 seconds and ~74%, and a page that contradicts itself two screens apart is
// worse than either number. «структурирует её в слайды» became «в документ» for the same reason —
// this product makes documents.
const FAQ_ITEMS = [
  {
    question: 'Что такое Textery AI и как работает нейросеть для текстовых документов?',
    answer:
      'Textery AI — это нейросеть для автоматического создания текстового документа с помощью искусственного интеллекта. Вы описываете тему доклада, эссе, реферата или сочинения — и получаете готовый профессиональный Word или PDF файл за 30 секунд. ИИ анализирует контент, создаёт структуру документа, генерирует текст, подбирает элементы оформления.',
  },
  {
    question: 'Можно ли редактировать сгенерированные текстовые документы?',
    answer:
      'Да, после генерации вы можете редактировать текстовый файл в онлайн-редакторе прямо в браузере или экспортировать в Word или PDF для дальнейшей работы. Меняйте тексты, цвета, шрифты, добавляйте свои изображения и диаграммы. Полный контроль над каждым элементом файла.',
  },
  {
    question: 'Чем Textery AI отличается от Gamma, Beautiful.ai и других конкурентов?',
    answer:
      'Textery AI — единственная нейросеть, изначально обученная на русском языке. Конкуренты используют автоперевод, что приводит к ошибкам и неестественным формулировкам. Также мы в 2 раза быстрее (30 сек против ~67 сек), точность экспорта в Word и PDF 98% против ~74% у конкурентов, оплата в рублях российскими картами, работа без VPN.',
  },
  {
    question: 'Какие форматы поддерживает экспорт текстового документа?',
    answer:
      'Вы можете экспортировать текстовый файл в форматы Word или PDF, или получить веб-ссылку для онлайн-просмотра. При экспорте в Word и PDF сохраняется 98% форматирования — шрифты, цвета, позиции элементов остаются на своих местах.',
  },
  {
    question: 'Как долго создается текстовый файл в Textery AI?',
    answer:
      'Весь процесс создания документа занимает не больше 45 секунд. Описываете нужную вам тему доклада, реферата, эссе или сочинения и нажимаете кнопку «Сгенерировать». Нужный текстовый документ уже перед вами!',
  },
  {
    question: 'Из каких источников можно создавать файл?',
    answer:
      'Textery AI создаёт текстовый файл из любых источников: просто текст или веб-страницы по URL. Нейросеть автоматически извлекает ключевую информацию и структурирует её в документ.',
  },
]

export function LandingFaq() {
  return (
    <section className={styles.faq} data-testid="landing-faq">
      <div className={styles['faq-head']}>
        <span className={landingSectionStyles['landing-eyebrow']}>FAQ</span>
        <h2 className={styles['faq-title']}>Часто задаваемые вопросы</h2>
        <p className={styles['faq-lead']}>
          Не тратьте время на поиск — мы собрали <strong>всё самое важное</strong> в одном месте
        </p>
      </div>

      <div className={styles['faq-list']}>
        {FAQ_ITEMS.map((item) => (
          <details className={styles['faq-item']} key={item.question}>
            <summary className={styles['faq-question']}>
              {item.question}
              <span className={styles['faq-marker']} aria-hidden="true" />
            </summary>
            <p className={styles['faq-answer']}>{item.answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
