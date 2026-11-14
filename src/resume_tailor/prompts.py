"""Agent prompts. Voice blocks and JSON schema ported from resume-transform."""

JSON_STRUCTURE = """
{
  "basics": {
    "name": "",
    "label": "",
    "email": "",
    "phone": "",
    "url": "",
    "summary": "",
    "location": {
      "city": "",
      "countryCode": "",
      "region": ""
    },
    "profiles": [
      {
        "network": "",
        "username": "",
        "url": ""
      }
    ]
  },
  "work": [
    {
      "name": "",
      "position": "",
      "location": "",
      "startDate": "",
      "endDate": "",
      "highlights": []
    }
  ],
  "education": [
    {
      "institution": "",
      "area": "",
      "studyType": "",
      "location": "",
      "startDate": "",
      "endDate": "",
      "gpa": "",
      "courses": []
    }
  ],
  "skills": [
    {
      "name": "",
      "keywords": []
    }
  ],
  "certificates": [
    {
      "name": "",
      "issuer": "",
      "date": ""
    }
  ],
  "projects": [
    {
      "name": "",
      "description": "",
      "highlights": [],
      "keywords": [],
      "url": ""
    }
  ],
  "languages": [
    {
      "language": "",
      "fluency": ""
    }
  ],
  "interests": [
    {
      "name": "",
      "keywords": []
    }
  ]
}
"""


_VOICE_EN = """VOICE: All resume text must be written in first person in English.
- Bullet points and highlights: use first-person past tense ("Developed", "Led", "Implemented", "Reduced", "Built").
- Summary: write as an implied first-person narrative starting with adjectives or role title (e.g., "Experienced software engineer with...").
- Never use third person ("He developed", "She led")."""

_VOICE_PTBR = """IDIOMA OBRIGATÓRIO — PORTUGUÊS BRASILEIRO:
ATENÇÃO: TODO o texto do currículo (sumário, cargos, bullets, habilidades, projetos) DEVE estar escrito em Português Brasileiro. Isso é inegociável.
- NÃO escreva nada em inglês no conteúdo do currículo, mesmo que a descrição da vaga esteja em inglês.
- Bullets e destaques: use verbos no passado em primeira pessoa ("Desenvolvi", "Liderei", "Implementei", "Reduzi", "Criei", "Automatizei").
- Sumário: narrativa em primeira pessoa implícita ("Profissional com mais de X anos...", "Engenheiro de Dados com sólida experiência em...").
- NUNCA use terceira pessoa ("Desenvolveu", "Liderou") — corrija qualquer verbo em terceira pessoa que encontrar.
- Se você escrever qualquer frase em inglês no conteúdo do currículo, sua resposta será rejeitada."""


def _voice(language: str) -> str:
    return _VOICE_EN if language.lower().startswith("en") else _VOICE_PTBR


ROLE_FOCUS = """ROLE FOCUS: the resume targets ONE role. Do not hedge between roles.
- `basics.label`, the summary and the skills order must present a single professional identity: the target role.
- TRINITY HUB EXCEPTION: in the Trinity Hub position, show ONLY the target role. The position title names only the target role (DevOps target: "DevOps"; Full-Stack target: "Engenheiro Full-Stack"), and the bullets keep only evidence of that role. Drop the other role's bullets entirely; the position itself stays.
- In the other positions, evidence for other roles stays (true, never removed from a position) but goes last and short; skills and keywords outside the target stay only as brief secondary items.
- Do not mention the other role by name or list its stack as an equal strength."""

SOURCE_RULES = """SOURCE RULES: profile_truth.md is the ONLY source of facts. Its corrections and exclusions are final.
- NEVER invent companies, titles, dates, metrics, skills or credentials. A number may appear only if that exact number is in profile_truth.md.
- Ignore placeholders and unconfirmed credentials. Keep expired certifications marked as expired and education in progress marked as in progress.
- ALWAYS include every academic degree. Never include family, health or other private personal context.
- Do not attribute general skills to a specific employer without evidence."""

BASIC_REQUIREMENTS = """BASIC REQUIREMENTS (ATS): read the job for its simple, baseline requirements: common tools, protocols and concepts, and soft skills. Use your own judgment to find them. Do not wait for a fixed list.
- For each one, decide if a professional with this candidate's documented experience and level would reasonably have it. If yes, put it in the resume where ATS and the recruiter will see it: `skills` keywords, the summary, or a bullet that fits. Use the job's own term.
- It does not need to be written word for word in profile_truth.md. Documented work can imply it. Skills and the summary are the safe places for these baseline items; do not tie one to a specific employer without evidence.
- Do not add what the documented experience cannot reasonably support, and never add metrics, employers, titles or credentials for it. Such a requirement stays a gap."""

OUTPUT_JSON = (
    "Reply with the resume as ONE valid JSON object in a fenced ```json block, "
    "following this schema:\n" + JSON_STRUCTURE
)


STRATEGIST_SYSTEM = (
    "You are a senior Career Strategist who repositions mid-career professionals for new roles. "
    "You never invent experience: you reframe, reorder and rewrite real experience to fit the target role."
)

HIRING_MANAGER_SYSTEM = (
    "You are an experienced hiring manager at a top company. "
    "You give specific, actionable, honest evaluations."
)

EDITOR_SYSTEM = (
    "You are an expert resume editor. You produce a complete, readable resume that applies the "
    "hiring manager's feedback and stays true to the candidate's real experience."
)


def strategist_prompt(job_description: str, truth: str, language: str) -> str:
    return f"""{_voice(language)}

{SOURCE_RULES}

{ROLE_FOCUS}

{BASIC_REQUIREMENTS}

### Target Job Description
{job_description}

### profile_truth.md
{truth}

Build the FIRST version of the resume from profile_truth.md, positioned for the target job:

1. Summary: 3-4 sentences (who the person is, what they bring, why they fit). Use the job's terms naturally.
2. Work: KEEP EVERY POSITION, current first, then reverse chronology. Never drop a company or role, even if unrelated.
   Inside each position put the most relevant evidence first, then keep every other distinct documented responsibility, project and result.
   Merge repetitions. Use STAR when possible. HARD LIMIT: the resume must fit ONE A4 page (about 450-550 words in total). Keep every position, but give old or unrelated roles 1-2 short bullets and the most relevant roles at most 3-4.
3. Skills: most relevant first. Add skill categories from the job only when the candidate really has them.
4. Projects and certifications: highlight those relevant to the role.
5. ATS: use the job's keywords naturally, no stuffing.

{OUTPUT_JSON}
"""


def hiring_manager_prompt(job_description: str, resume: dict, truth: str) -> str:
    return f"""### Job Description
{job_description}

### Candidate's Resume
{resume}

### profile_truth.md (the only source of facts)
{truth}

Evaluate:
1. Overall rating 1-10 with a short reason.
2. Strengths (3-5), each with its relevance to the role.
3. Areas for improvement (3-5): why it matters, and how to address it in the resume truthfully.
4. Missing keywords or ATS gaps, and how to add them truthfully. Check the job's baseline requirements (common tools, concepts, soft skills): flag each one the candidate's experience reasonably supports but the resume does not show.
5. Presentation feedback (2-3 suggestions).
6. Coverage: check each position against profile_truth.md and list any documented evidence missing from the resume. The resume must fit ONE page: prefer concise bullets, and flag only high-value missing evidence.

Rate only evidence written in the resume and supported by profile_truth.md. A requirement the candidate cannot truthfully cover stays a gap: list it, do not raise the rating for claims without evidence.

The LAST line of your answer MUST be exactly: FINAL_RATING: <number from 1 to 10, one decimal allowed>
"""


def editor_prompt(job_description: str, resume: dict, truth: str, feedback: str, language: str, audit: bool = True) -> str:
    audit_step = AUDIT_STEP if audit else ""
    audit_reply = AUDIT_REPLY if audit else ""
    return f"""{_voice(language)}

{SOURCE_RULES}

{ROLE_FOCUS}

{BASIC_REQUIREMENTS}

### Job Description
{job_description}

### Current Version (to improve)
{resume}

### profile_truth.md (source of truth)
{truth}

### Hiring Manager's Latest Evaluation
{feedback}

Steps:
1. Address every gap and suggestion from the evaluation. A gap the sources cannot cover stays a gap. Never fabricate to raise the rating.
2. The `work` array MUST contain every company and position of profile_truth.md, current first, then reverse chronology. Within each position, vacancy-relevant evidence first, keep only the strongest other evidence. HARD LIMIT: the resume must fit ONE A4 page (about 450-550 words in total): condense, merge and cut the least relevant bullets (never a whole position).
3. Use strong action verbs. Keep the same JSON schema:
{JSON_STRUCTURE}
{audit_step}

Reply in this exact order:
1. The final resume as ONE valid JSON object in a fenced ```json block.{audit_reply}
"""


AUDIT_STEP = """4. Coverage audit: for EACH position list the source themes from profile_truth.md, the final bullets that cover them, and any omission. Cuts needed to fit one page are acceptable omissions: mark them as such."""
AUDIT_REPLY = """
2. Then a markdown section starting with the line "## Coverage audit"."""
