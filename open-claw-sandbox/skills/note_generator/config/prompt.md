## Phase 5: Note Synthesis Instruction
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

## Phase 5 Part A: Chunk Summary Extraction Instruction
**Role**: You are extracting core concepts for a Map-Reduce aggregation pipeline.
**Task**: Read the transcript chunk and extract the absolute most important academic points, numbers, and case studies.
**Constraint**: Output succinct bullet points. DO NOT output conversational filler.

<transcript>
{INPUT_CONTENT}
</transcript>

---

## Phase 3 Map: Concept Extraction (PDF/Documents)
**Role**: You are an Academic Synthesizer Map-Reduce framework node.
**Task**: Extract core knowledge points, definitions, data, and formula derivations from the provided PDF text chunk. The input may contain OCR errors or broken line breaks.

**⚠️ RULE**:
1. Output MUST be structured in rich Markdown notes.
2. DO NOT include conversational filler or hallucinate information not present in the chunk.
3. Focus ONLY on academic substance.

**Format**: Markdown headings and bullet points.

【Source Content】:
{INPUT}

---

## Phase 3 Reduce: Final Synthesis (PDF/Documents)
**Role**: You are an elite Knowledge Base Architect.
**Task**: Merge AI-extracted chunk notes and VLM image descriptions into a unified and extremely high-quality final document.

**⚠️ RULE**:
1. You MUST use clear hierarchy (`#`, `##`, `###`).
2. You MUST NOT lose any mathematical formulas, critical data, or proper nouns from the Map nodes.
3. If the figure list contains relevant VLM descriptions, you MUST integrate them logically into the corresponding text sections.
4. The final output MUST be seamlessly cohesive without reading like disjointed chunks.
5. All terminology MUST strictly adhere to the provided Glossary/Term Protection constraints.
6. Absolutely NO summaries or conversational wrap-ups at the end. Provide the pure academic note directly.

**Format**: Final Knowledge Base Markdown.

{GLOSSARY}

【Figure List & Analysis】:
{FIGURES}

【Section Key Notes】:
{NOTES}
