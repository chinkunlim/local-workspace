## Phase 5: 筆記合成指令
**Role**: Knowledge Management Expert.
**Task**: Transform transcript into hybrid high-utility notes.

**Output Structure (Strict Order)**:
1. **Title**: Formal Subject
2. **🎓 3 Key Learning Points**: Bulleted list
3. **📝 Lecture Notes (Cornell Format)**: Markdown table (Cues | Notes) + Summary.
4. **🧠 Mind Map (Mermaid)**: `mermaid` mindmap block.
5. **💡 QEC**: Question-Evidence-Conclusion
6. **👶 Feynman Technique**: Analogy
7. **🏷️ Hashtags**: `#tags`

**Constraint**: Grounded ONLY in the provided text.

<materials>
{INPUT_CONTENT}
</materials>

---

## Phase 5 Part A: 分塊摘要提取指令
**Role**: You are extracting core concepts for a Map-Reduce aggregation pipeline.
**Task**: Read the transcript chunk and extract the absolute most important academic points, numbers, and case studies.
**Constraint**: Output succinct bullet points. DO NOT output conversational filler.

<transcript>
{INPUT_CONTENT}
</transcript>
