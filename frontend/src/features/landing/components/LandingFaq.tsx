import './LandingFaq.css'

// Figma `Desktop` (node 90:880), y=2159: four 850x70 white rows at 10px radius, each with a
// `+` glyph at the right edge. The design shows every row collapsed, so the answer copy is
// not in the file — the text below is written from what the product actually does and is
// pending a copy review, not lifted from a mockup.
const FAQ_ITEMS = [
  {
    question: 'Что такое Textery AI?',
    answer:
      'Сервис, который генерирует доклады, рефераты, эссе и сочинения по теме, которую вы описали, и сразу оформляет их как готовый документ.',
  },
  {
    question: 'Можно ли редактировать сгенерированный файл?',
    answer:
      'Да. После генерации документ открывается в редакторе, где текст и оформление можно менять вручную.',
  },
  {
    question: 'Какие форматы поддерживают экспорт сгенерированные файлы?',
    answer: 'Готовый документ выгружается в Word и PDF без сжатия и искажений вёрстки.',
  },
  {
    question: 'Из каких источников можно создавать доклады?',
    answer:
      'Достаточно описать тему своими словами — модель собирает структуру и содержание документа сама.',
  },
]

export function LandingFaq() {
  return (
    <section className="faq" data-testid="landing-faq">
      <h2 className="faq-title">Часто задаваемые вопросы</h2>

      <div className="faq-list">
        {FAQ_ITEMS.map((item) => (
          <details className="faq-item" key={item.question}>
            <summary className="faq-question">
              {item.question}
              <span className="faq-marker" aria-hidden="true" />
            </summary>
            <p className="faq-answer">{item.answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
