import { Fragment, type ReactNode } from "react";

/**
 * Markdown tối giản cho câu trả lời của agent: **đậm**, danh sách "-"/"1.", tiêu đề "#", link http(s).
 * Dựng thành React node — không dùng dangerouslySetInnerHTML, nên nội dung từ LLM không thể chèn HTML/script.
 */
const INLINE = /(\*\*[^*]+\*\*|https?:\/\/[^\s)\]]+)/g;

function inline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (/^https?:\/\//.test(part)) {
      const url = part.replace(/[.,;]+$/, "");
      return <Fragment key={i}><a href={url} target="_blank" rel="noopener noreferrer">{url}</a>{part.slice(url.length)}</Fragment>;
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];
  let ordered = false;

  const flush = () => {
    if (!listItems.length) return;
    const items = listItems.map((li, i) => <li key={i}>{inline(li)}</li>);
    blocks.push(ordered ? <ol key={blocks.length}>{items}</ol> : <ul key={blocks.length}>{items}</ul>);
    listItems = [];
  };

  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
    const num = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    if (bullet || num) {
      if (listItems.length && ordered !== !!num) flush();
      ordered = !!num;
      listItems.push((bullet ?? num)![1]);
      continue;
    }
    flush();
    if (!line.trim()) continue;
    const heading = /^#{1,4}\s+(.*)$/.exec(line);
    blocks.push(heading ? <p key={blocks.length}><strong>{inline(heading[1])}</strong></p>
                        : <p key={blocks.length}>{inline(line)}</p>);
  }
  flush();
  return <>{blocks}</>;
}
