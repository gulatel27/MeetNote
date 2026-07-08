function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split(/(?<!\\)\|/)
    .map((cell) => cell.replace(/\\\|/g, "|").trim());
}

function isTableSeparator(line) {
  return /^\|\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$/.test(line.trim());
}

function escapeTableCell(value) {
  return String(value ?? "").replace(/\|/g, "\\|").replace(/\n/g, " ").trim();
}

function parseMarkdown(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let list = [];
  let table = [];
  let transcriptLines = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  };

  const flushList = () => {
    if (list.length) {
      blocks.push({ type: "list", items: list });
      list = [];
    }
  };

  const flushTable = () => {
    if (table.length) {
      const rows = table.filter((line) => !isTableSeparator(line)).map(splitTableRow);
      blocks.push({ type: "table", rows });
      table = [];
    }
  };

  const flushInline = () => {
    flushParagraph();
    flushList();
    flushTable();
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (transcriptLines) {
      transcriptLines.push(line);
      continue;
    }

    if (!trimmed) {
      flushInline();
      continue;
    }

    if (trimmed.startsWith("## 8.")) {
      flushInline();
      blocks.push({ type: "h2", text: trimmed.replace(/^##\s+/, "") });
      transcriptLines = [];
      continue;
    }

    if (trimmed.startsWith("# ")) {
      flushInline();
      blocks.push({ type: "h1", text: trimmed.replace(/^#\s+/, "") });
      continue;
    }

    if (trimmed.startsWith("## ")) {
      flushInline();
      blocks.push({ type: "h2", text: trimmed.replace(/^##\s+/, "") });
      continue;
    }

    if (trimmed.startsWith("### ")) {
      flushInline();
      blocks.push({ type: "h3", text: trimmed.replace(/^###\s+/, "") });
      continue;
    }

    if (trimmed.startsWith("|")) {
      flushParagraph();
      flushList();
      table.push(trimmed);
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      flushParagraph();
      flushTable();
      list.push(trimmed.replace(/^[-*]\s+/, ""));
      continue;
    }

    flushList();
    flushTable();
    paragraph.push(trimmed);
  }

  flushInline();
  if (transcriptLines) {
    blocks.push({ type: "transcript", text: transcriptLines.join("\n").trim() });
  }
  return blocks;
}

function splitIntoSections(blocks) {
  const sections = [];
  let title = null;
  let current = null;

  for (const block of blocks) {
    if (block.type === "h1") {
      title = block;
      continue;
    }

    if (block.type === "h2") {
      current = { title: block.text, blocks: [] };
      sections.push(current);
      continue;
    }

    if (!current) {
      current = { title: "보고서", blocks: [] };
      sections.push(current);
    }
    current.blocks.push(block);
  }

  return { title, sections };
}

function modelToMarkdown(model) {
  const lines = [];
  if (model.title?.text) {
    lines.push(`# ${model.title.text.trim()}`);
  }

  for (const section of model.sections) {
    lines.push("", `## ${section.title.trim()}`, "");

    for (const block of section.blocks) {
      if (block.type === "h3") {
        lines.push(`### ${block.text.trim()}`, "");
      } else if (block.type === "list") {
        block.items.forEach((item) => lines.push(`* ${String(item).trim() || "미정"}`));
        lines.push("");
      } else if (block.type === "table" && block.rows.length) {
        const [head, ...body] = block.rows;
        lines.push(`| ${head.map(escapeTableCell).join(" | ")} |`);
        lines.push(`| ${head.map(() => "--").join(" | ")} |`);
        body.forEach((row) => lines.push(`| ${row.map(escapeTableCell).join(" | ")} |`));
        lines.push("");
      } else if (block.type === "transcript") {
        lines.push(block.text.trim(), "");
      } else if (block.text?.trim()) {
        lines.push(block.text.trim(), "");
      }
    }
  }

  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
}

function sectionTone(title) {
  if (title.includes("핵심요약") || title.includes("회의 요약")) return "summary";
  if (title.includes("내용 요약") || title.includes("논의")) return "discussion";
  if (title.includes("청중")) return "action";
  if (title.includes("결정")) return "decision";
  if (title.includes("이슈") || title.includes("리스크")) return "risk";
  if (title.includes("액션")) return "action";
  if (title.includes("후속")) return "follow";
  if (title.includes("Transcript")) return "transcript";
  return "info";
}

function EditableText({ className = "", minRows = 1, onChange, value }) {
  return (
    <textarea
      className={`inline-editor ${className}`}
      onChange={(event) => onChange(event.target.value)}
      rows={minRows}
      value={value}
    />
  );
}

function renderReadOnlyBlock(block, index) {
  if (block.type === "h3") {
    return (
      <h3 className="report-subtitle" key={index}>
        {block.text}
      </h3>
    );
  }

  if (block.type === "list") {
    return (
      <ul className="report-list" key={index}>
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>{item}</li>
        ))}
      </ul>
    );
  }

  if (block.type === "table" && block.rows.length) {
    const [head, ...body] = block.rows;
    return (
      <div className="report-table-wrap" key={index}>
        <table className="report-table">
          <thead>
            <tr>
              {head.map((cell, cellIndex) => (
                <th key={cellIndex}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === "transcript") {
    return (
      <pre className="report-transcript" key={index}>
        {block.text || "Transcript가 없습니다."}
      </pre>
    );
  }

  return (
    <p className="report-paragraph" key={index}>
      {block.text}
    </p>
  );
}

function renderEditableBlock(block, index, updateBlock) {
  if (block.type === "h3") {
    return (
      <EditableText
        className="subtitle-editor"
        key={index}
        onChange={(text) => updateBlock({ ...block, text })}
        value={block.text}
      />
    );
  }

  if (block.type === "list") {
    return (
      <ul className="report-list report-list-editable" key={index}>
        {block.items.map((item, itemIndex) => (
          <li key={itemIndex}>
            <EditableText
              className="list-item-editor"
              minRows={2}
              onChange={(text) => {
                const items = [...block.items];
                items[itemIndex] = text;
                updateBlock({ ...block, items });
              }}
              value={item}
            />
          </li>
        ))}
      </ul>
    );
  }

  if (block.type === "table" && block.rows.length) {
    const [head, ...body] = block.rows;
    return (
      <div className="report-table-wrap" key={index}>
        <table className="report-table report-table-editable">
          <thead>
            <tr>
              {head.map((cell, cellIndex) => (
                <th key={cellIndex}>{cell}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex}>
                    <EditableText
                      className="table-cell-editor"
                      onChange={(text) => {
                        const rows = block.rows.map((nextRow) => [...nextRow]);
                        rows[rowIndex + 1][cellIndex] = text;
                        updateBlock({ ...block, rows });
                      }}
                      value={cell}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (block.type === "transcript") {
    return (
      <EditableText
        className="transcript-editor"
        key={index}
        minRows={8}
        onChange={(text) => updateBlock({ ...block, text })}
        value={block.text}
      />
    );
  }

  return (
    <EditableText
      className="paragraph-editor"
      key={index}
      minRows={2}
      onChange={(text) => updateBlock({ ...block, text })}
      value={block.text}
    />
  );
}

export default function MarkdownReport({ isEditing = false, markdown, onChange }) {
  if (!markdown) {
    return <div className="empty-state">생성된 보고서가 없습니다.</div>;
  }

  const model = splitIntoSections(parseMarkdown(markdown));

  const updateTitle = (text) => {
    onChange?.(modelToMarkdown({ ...model, title: { type: "h1", text } }));
  };

  const updateBlock = (sectionIndex, blockIndex, nextBlock) => {
    const sections = model.sections.map((section, currentSectionIndex) => {
      if (currentSectionIndex !== sectionIndex) {
        return section;
      }
      return {
        ...section,
        blocks: section.blocks.map((block, currentBlockIndex) =>
          currentBlockIndex === blockIndex ? nextBlock : block,
        ),
      };
    });
    onChange?.(modelToMarkdown({ ...model, sections }));
  };

  return (
    <div className={`markdown-report ${isEditing ? "is-editing" : ""}`}>
      {model.title ? (
        <div className="report-title">
          {isEditing ? (
            <EditableText className="title-editor" onChange={updateTitle} value={model.title.text} />
          ) : (
            <h1>{model.title.text}</h1>
          )}
        </div>
      ) : null}

      {model.sections.map((section, sectionIndex) => (
        <section className={`report-section report-section-${sectionTone(section.title)}`} key={sectionIndex}>
          <header className="report-section-header">
            <h2>{section.title}</h2>
          </header>
          <div className="report-section-body">
            {section.blocks.map((block, blockIndex) =>
              isEditing
                ? renderEditableBlock(block, blockIndex, (nextBlock) =>
                    updateBlock(sectionIndex, blockIndex, nextBlock),
                  )
                : renderReadOnlyBlock(block, blockIndex),
            )}
          </div>
        </section>
      ))}
    </div>
  );
}
