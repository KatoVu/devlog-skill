# Writing guide

The post is the author's, written in first person about work they did. A reader should come away
knowing one thing they didn't know before, and believing it, because the post showed them.

## Angles

One post defends one thesis. Strong angles, roughly in order:

1. **A hard problem and how it was solved.** "Replaying a refresh token now ends the whole grant.
   Here's why that's the only safe answer." It needs the code that solves it and, ideally, the
   author's account of what didn't work first.
2. **A design decision and its trade-off.** "Why the access token is just an API token with an
   expiry." It needs the alternatives that were considered, which the author supplies or the code
   shows.
3. **How a feature works, end to end.** A request traced through the layers. It needs real code
   at each hop and a diagram.
4. **What building it taught.** Only with the author's own material. You can't invent lessons.
5. **Project overview.** Only for small projects, or as the first post about one.

Name the thesis in one sentence before outlining. If you can't, the angle is too vague.

## Structure

- **Title.** Specific and plain. "Letting an AI write drafts without ever letting it delete"
  beats "Building a Secure AI Integration". No colons with clickbait after them. No "How I…"
  unless it really is a personal story.
- **Opening (1–2 paragraphs).** Start with the problem, concretely: what broke, what was missing,
  what a user ran into. No throat-clearing, no "in today's world", no definition of words the
  reader already knows.
- **Body (3–6 sections).** Each section moves the thesis forward. Headings say what the section
  establishes ("Refresh tokens rotate, and replay ends the grant"), not just its topic
  ("Refresh tokens").
- **Trade-offs.** Say what this approach costs, what it doesn't handle, and what you'd change.
  That makes the rest believable.
- **Ending.** What's next, or the one idea to keep. Don't recap. No "In conclusion".

Length: 1,200–2,500 words of prose, unless the author asks for something else. Long enough to
show real code, short enough to finish.

## Code excerpts

- Real code from the repository, never paraphrased into code. You can trim lines, but mark the
  cut with `// …` (or the language's comment), and never change what a line does.
- At most about 25 lines per excerpt. Show the lines that carry the idea, not the scaffolding.
- Always give a language on the fence. Put the file path in the sentence before it or in a
  comment on the first line: `// backend/Services/OAuthService.cs`.
- Explain *why* after each excerpt, in prose. A block of code with no explanation after it is
  padding.
- Never show secrets, internal hostnames, or `.env` contents, even ones that look fake.

## Diagrams

Use Mermaid for architecture, sequences and state, in ` ```mermaid ` blocks. One diagram per
idea, with at most about 10 nodes. Label the edges with what actually travels along them
("bearer token", "form post"), not "data".

## Voice

- First person, from the author. Use "I" for one author and "we" for a team, whichever the author
  uses in their interview answers or style file.
- Plain, concrete and confident about what the code shows. Hedge only where the author is unsure.
- Keep sentences short. Paragraphs run 2–4 sentences.
- Match the author's register from `style.md`, or from samples they point you to.

Avoid, because they mark text as machine-written and say nothing:

- "delve", "leverage", "robust", "seamless", "cutting-edge", "game-changer", "unlock",
  "supercharge", "elevate", "in the realm of", "it's worth noting", "at the end of the day"
- opening with a question to the reader, or with a dictionary definition
- triplets of adjectives, and paragraphs that end with a one-line moral
- "Let's dive in", "In this post, I will…" (just do it), "Happy coding!"
- superlatives you can't prove: "blazing fast", "the best way", "production-grade"
- emoji in headings

## Numbers and claims

- A number needs a source: a command you ran (give it in `claims.md`), or the author.
- Don't round up, and don't extrapolate ("could handle millions").
- Comparisons ("3× faster than…") need both sides measured the same way, or they're cut.
- Name versions when behaviour depends on them ("Next.js 16", "MCP SDK 2.3").

## Front matter fields

| Field | Rule |
| --- | --- |
| `title` | 3–200 characters |
| `slug` | lowercase words joined by single hyphens, ≤ 200 characters |
| `summary` | ≤ 500 characters. One or two sentences: what it is and why it's interesting. Shown on the card |
| `repo_url` | Only a public remote. Strip credentials. Ask if you can't tell whether it's public |
| `demo_url` | Only if the author gave one |
| `source_commit` | `git rev-parse --short HEAD` at the time of writing |
