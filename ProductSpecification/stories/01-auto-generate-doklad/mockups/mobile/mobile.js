// Мобильный лэндинг: карусель преимуществ и переключение колонки в таблице сравнения.
// Обе вещи существуют только на 360 px — на десктопе метрики стоят рядом, а таблица трёхколоночная.

const track = document.getElementById('qualityTrack')
const dots = [...document.getElementById('qualityDots').children]

function showSlide(index) {
  track.style.transform = `translateX(-${index * 100}%)`
  dots.forEach((dot, i) => dot.setAttribute('aria-current', String(i === index)))
}

dots.forEach((dot, i) => dot.addEventListener('click', () => showSlide(i)))

// Свайп пальцем — тот же жест, что и точки, чтобы листать не целясь в 7-пиксельную мишень.
let startX = null
track.addEventListener('touchstart', (event) => {
  startX = event.touches[0].clientX
})
track.addEventListener('touchend', (event) => {
  if (startX === null) return
  const delta = event.changedTouches[0].clientX - startX
  const current = dots.findIndex((dot) => dot.getAttribute('aria-current') === 'true')
  if (Math.abs(delta) > 40) showSlide(Math.min(dots.length - 1, Math.max(0, current + (delta < 0 ? 1 : -1))))
  startX = null
})

const tabs = [...document.getElementById('compareTabs').children]
const values = [...document.querySelectorAll('#compareTable .compare__cell--value')]

tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => {
    tabs.forEach((item, i) => item.setAttribute('aria-selected', String(i === index)))
    values.forEach((cell) => {
      const text = index === 0 ? cell.dataset.own : cell.dataset.rival
      cell.innerHTML = text.replace('✓', '<span class="compare__ok">✓</span>')
        .replace('✕', '<span class="compare__no">✕</span>')
    })
  })
})

tabs[0].click()

// Переключатель темы в шапке — тема живёт на <html data-theme>, как в десктопном мокапе.
document.addEventListener('click', (event) => {
  if (!event.target.closest('.topbar__toggle')) return
  const root = document.documentElement
  root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark'
})

// Макет нарисован на фиксированной канве (1920 на десктопе, 360 на мобильной) и остаётся
// эталоном в пикселях Figma. Чтобы открыть его на экране другой ширины, канва не
// переверстывается, а ужимается целиком: zoom, в отличие от transform, сжимает и высоту
// документа, поэтому страница не тянет за собой пустую полосу прокрутки. Шире канвы масштаб не
// растёт — макет просто центрируется.
const CANVAS_WIDTH = 360

function fitCanvas() {
  const page = document.querySelector('.page')
  if (page) page.style.zoom = String(Math.min(1, window.innerWidth / CANVAS_WIDTH))
}

fitCanvas()
window.addEventListener('resize', fitCanvas)
