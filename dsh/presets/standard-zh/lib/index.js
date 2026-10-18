/**
 * 中文标准预设的提示词改写插件。
 *
 * 该插件随预设一起挂载在预设 scope 上，因此对预设内会话可见。它在
 * `system-prompt/assemble` 瀑布里拿到已经合并、排序、解析完动态文本的系统提示词
 * 段落，逐段调用 `localizePromptText`，把英文原文替换为中文译文；未命中的段落
 * 保持英文，指向同一提示词的其他段落文本（例如工具目录）不受影响。
 *
 * 选这个扩展点而不是「在预设里注册同名段」的原因：同名段只在跨 scope 时才能
 * 遮蔽，而标准预设的工具段、计划模式段与本插件同处预设 scope，重复注册会抛错；
 * 全局 scope 的段（身份、Web GUI、MCP 资源、交付物引用）与本插件也不在同层。
 */
import { localizePromptText } from './prompts.js'

export const name = 'dsh-preset-standard-zh'

/**
 * 把合并后的提示词段落译为中文。
 * @param ctx - 预设 scope 的插件上下文。
 */
export function apply(ctx) {
  ctx.on('system-prompt/assemble', async (assembly, _context, next) => {
    // next() 返回内层监听器或注册表产出的最终 assembly；本层只改段文本。
    const assembled = await next()
    const sections = assembled.sections.map((section) => {
      const text = localizePromptText(section.text)
      return text === section.text ? section : { ...section, text }
    })
    return { ...assembled, sections }
  })
}
