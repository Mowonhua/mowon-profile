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
 * 追加在系统提示词末尾的语言段落名。改名会导致重复添加，两者需保持一致。
 */
const LANGUAGE_SECTION_NAME = 'preset-zh:language'

/**
 * 语言要求段落。
 *
 * 只把系统提示词译成中文不会改变模型的推理语言：推理语言由模型默认行为和
 * 请求中的语言信号共同决定，与提示词语言没有绑定关系。要让模型用中文思考，
 * 必须在提示词里显式要求。该段落在瀑布返回前追加，位于已排序段落的末尾。
 */
const LANGUAGE_SECTION_TEXT = [
  '# 语言要求',
  '',
  '内部推理（思考）与最终答复一律使用简体中文。',
  '代码、命令、文件路径、工具名与参数名、日志、引用原文保持原样，不要翻译。',
  '用户明确要求使用其他语言时，以用户要求为准。',
].join('\n')

/**
 * 把合并后的提示词段落译为中文，并补上语言要求。
 * @param ctx - 预设 scope 的插件上下文。
 */
export function apply(ctx) {
  ctx.on('system-prompt/assemble', async (assembly, _context, next) => {
    // next() 返回内层监听器或注册表产出的最终 assembly；本层只改段文本与追加段落。
    const assembled = await next()
    const sections = assembled.sections.map((section) => {
      const text = localizePromptText(section.text)
      return text === section.text ? section : { ...section, text }
    })
    // 以段名去重：同一个 assembly 被多层监听器重复处理时不重复追加。
    if (!sections.some((section) => section.name === LANGUAGE_SECTION_NAME)) {
      sections.push({ name: LANGUAGE_SECTION_NAME, text: LANGUAGE_SECTION_TEXT })
    }
    return { ...assembled, sections }
  })
}
