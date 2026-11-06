/**
 * 独立示例：无依赖、面板级事件、单共享高亮、短时可改道 CSS transition。
 * 此示例为单列非滚动菜单。生产环境请按 references/implementation.md
 * 扩展动态内容、嵌套滚动裁剪与面板缩放支持。
 */
(() => {
  'use strict';

  const panel = document.querySelector('[data-glide-menu]');
  const layer = panel?.querySelector('[data-glide-layer]');
  const selectedLabel = document.getElementById('selected-label');
  if (!(panel instanceof HTMLElement) || !(layer instanceof HTMLElement)) return;

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const moveTransition =
    'transform var(--motion-instant) var(--motion-ease-out), ' +
    'opacity var(--motion-instant) var(--motion-ease-out)';
  const fadeOutTransition = 'opacity var(--motion-instant) var(--motion-ease-in)';
  const rows = () => Array.from(panel.querySelectorAll('[data-glide-item]'));
  const eligible = (row) =>
    row instanceof HTMLElement && row.isConnected &&
    row.getAttribute('aria-disabled') !== 'true' && !row.hasAttribute('disabled');

  let active = null;
  let pointer = null;
  let mode = 'idle';
  let frame = 0;
  let repositionWithoutSlide = false;

  function place(row) {
    const p = panel.getBoundingClientRect();
    const r = row.getBoundingClientRect();
    // 此示例面板自身不滚动、不缩放；复杂情况参见参考实现指引。
    layer.style.width = `${r.width}px`;
    layer.style.height = `${r.height}px`;
    layer.style.transform = `translate3d(${r.left - p.left - panel.clientLeft}px, ${r.top - p.top - panel.clientTop}px, 0)`;
  }

  function show(row) {
    if (row === active) return;
    if (active) active.removeAttribute('data-glide-active');
    if (!row) {
      layer.style.transition = reducedMotion.matches ? 'none' : fadeOutTransition;
      layer.style.opacity = '0';
      active = null;
      return;
    }

    if (!active) {
      const checked = rows().find((r) => r.getAttribute('aria-checked') === 'true' && eligible(r));
      layer.style.transition = 'none';
      place(reducedMotion.matches ? row : (checked || row));
      layer.style.opacity = '0';
      // 仅在入场时提交起始样式，避免每帧强制布局。
      void layer.offsetWidth;
    }
    layer.style.transition = reducedMotion.matches ? 'none' : moveTransition;
    place(row);
    layer.style.opacity = '1';
    row.setAttribute('data-glide-active', '');
    active = row;
  }

  function nearest(x, y) {
    const bounds = panel.getBoundingClientRect();
    if (x < bounds.left || x > bounds.right || y < bounds.top || y > bounds.bottom) return null;
    let closest = null;
    let min = Infinity;
    for (const row of rows()) {
      const r = row.getBoundingClientRect();
      const distance = y < r.top ? r.top - y : (y > r.bottom ? y - r.bottom : 0);
      if (distance < min) { min = distance; closest = row; }
    }
    return eligible(closest) ? closest : null;
  }

  function update() {
    if (mode === 'pointer' && pointer) {
      show(nearest(pointer.x, pointer.y));
      return;
    }
    if (mode === 'keyboard') {
      const focused = document.activeElement;
      show(rows().includes(focused) && eligible(focused) ? focused : null);
      return;
    }
    show(null);
  }

  function flush() {
    frame = 0;
    if (repositionWithoutSlide && active && active.isConnected) {
      layer.style.transition = 'none';
      place(active);
      // 提交瞬时校正，避免后续 transition 将滚动误当成动画。
      void layer.offsetWidth;
    }
    repositionWithoutSlide = false;
    update();
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(flush);
  }

  panel.addEventListener('pointermove', (e) => {
    mode = 'pointer';
    pointer = { x: e.clientX, y: e.clientY };
    schedule();
  });
  panel.addEventListener('pointerleave', () => {
    pointer = null;
    mode = 'idle';
    show(null);
  });
  panel.addEventListener('focusin', () => {
    mode = 'keyboard';
    pointer = null;
    schedule();
  });
  panel.addEventListener('focusout', (e) => {
    if (!panel.contains(e.relatedTarget)) {
      mode = 'idle';
      schedule();
    }
  });
  window.addEventListener('resize', () => {
    repositionWithoutSlide = true;
    schedule();
  });

  // 教学 demo 的方向键操作；集成 Radix 等菜单库时请移除，由菜单库管理焦点。
  panel.addEventListener('keydown', (e) => {
    const enabled = rows().filter(eligible);
    let n = enabled.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') n = (n + 1) % enabled.length;
    else if (e.key === 'ArrowUp') n = (n - 1 + enabled.length) % enabled.length;
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = enabled.length - 1;
    else return;
    if (!enabled.length) return;
    e.preventDefault();
    enabled[n].focus();
  });

  panel.addEventListener('click', (e) => {
    const target = e.target instanceof Element ? e.target.closest('[data-glide-item]') : null;
    if (!eligible(target)) return;
    for (const row of rows()) row.setAttribute('aria-checked', String(row === target));
    if (selectedLabel) selectedLabel.textContent = target.querySelector('.label')?.textContent ?? '';
  });
})();
