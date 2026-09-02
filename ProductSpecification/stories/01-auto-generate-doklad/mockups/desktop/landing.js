// Мокап: переключатель светлой и тёмной темы. Тема живёт на <html data-theme>,
// весь остальной CSS читает её через переменные из landing-tokens.css.
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
const CANVAS_WIDTH = 1920

function fitCanvas() {
  const page = document.querySelector('.page')
  if (page) page.style.zoom = String(Math.min(1, window.innerWidth / CANVAS_WIDTH))
}

fitCanvas()
window.addEventListener('resize', fitCanvas)
