#!/usr/bin/env node
// 交互界面写入 stderr，stdout 仅输出选中的名称，供两个安装脚本读取。
const readline = require('readline');

const names = process.argv.slice(2);
if (!process.stdin.isTTY || !process.stderr.isTTY || names.length === 0) process.exit(1);

const selected = new Set();
let cursor = 0;
let lines = 0;
readline.emitKeypressEvents(process.stdin);
process.stdin.setRawMode(true);
process.stdin.resume();

function render() {
  if (lines) process.stderr.write(`\x1b[${lines}A`);
  const height = Math.max(1, (process.stderr.rows || 24) - 4);
  const start = Math.min(Math.max(0, cursor - height + 1), Math.max(0, names.length - height));
  const visible = names.slice(start, start + height);
  const rows = ['  Select skills to remove (↑/↓ move, space select, enter confirm, q cancel)'];
  for (let i = 0; i < visible.length; i++) {
    const index = start + i;
    rows.push(`  ${index === cursor ? '❯' : ' '} ${selected.has(index) ? '◉' : '◯'} ${visible[i]}`);
  }
  if (names.length > height) rows.push(`  ${cursor + 1}/${names.length}`);
  for (const row of rows) process.stderr.write(`\r\x1b[2K${row}\n`);
  lines = rows.length;
}

function finish(cancelled) {
  process.stdin.setRawMode(false);
  process.stdin.pause();
  if (!cancelled) {
    for (const [index, name] of names.entries()) if (selected.has(index)) process.stdout.write(`${name}\n`);
  }
  process.exit(cancelled ? 2 : 0);
}

process.stdin.on('keypress', (character, key = {}) => {
  if (key.ctrl && key.name === 'c' || key.name === 'escape' || character === 'q') return finish(true);
  if (key.name === 'return' || key.name === 'enter') return finish(false);
  if (key.name === 'up') cursor = (cursor + names.length - 1) % names.length;
  else if (key.name === 'down') cursor = (cursor + 1) % names.length;
  else if (key.name === 'space') selected.has(cursor) ? selected.delete(cursor) : selected.add(cursor);
  else return;
  render();
});
render();
