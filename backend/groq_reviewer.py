import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


LANGUAGE_FOCUS = {
    "Python": "PEP 8, type hints, mutable default arguments, bare except, context managers, SQL injection via f-strings, pickle/eval/exec misuse",
    "JavaScript": "var vs let/const, == vs ===, unhandled promises, async/await errors, XSS via innerHTML, eval, prototype pollution, callback hell",
    "TypeScript": "use of any, missing strict null checks, unsafe type assertions, unhandled promises, enums vs unions, XSS via innerHTML",
    "Java": "null handling and Optional, resource leaks (try-with-resources), equals/hashCode contracts, thread safety, checked exception misuse, SQL injection",
    "C++": "memory leaks and RAII, dangling pointers, buffer overflows, rule of three/five, undefined behaviour, use of raw new/delete, const-correctness",
    "C": "buffer overflows, unchecked malloc, memory leaks, use-after-free, integer overflow, format string bugs, unsafe string functions",
    "Go": "unchecked errors, goroutine leaks, data races, defer in loops, nil maps, context propagation, SQL injection",
    "Rust": "unwrap/expect in production paths, unnecessary clones, unsafe blocks, lifetime problems, error handling with Result, blocking in async code",
    "SQL": "SQL injection, missing indexes, SELECT *, N+1 queries, missing transactions, unbounded queries",
}


def review_code(code, memories, language="Python"):
    memory_text = "\n\n".join(
        memory.text
        for memory in memories
    ) or "(no relevant team memory yet)"

    focus = LANGUAGE_FOCUS.get(language, "idiomatic style, error handling, security and performance")

    prompt = f"""
You are a senior {language} engineer performing a code review.

Review the following {language} code using both:
1. The submitted code
2. Relevant knowledge remembered from the team's previous decisions and reviews

====================
CODE TO REVIEW ({language})
====================

{code}

====================
TEAM MEMORY
====================

{memory_text}

====================
REVIEW REQUIREMENTS
====================

Analyze the code for:

1. Bugs and logical errors
2. Security vulnerabilities
3. Architecture violations
4. Maintainability problems
5. Performance concerns
6. Team-specific issues based on the provided memory
7. {language}-specific pitfalls: {focus}

For every important issue, explain:
- Severity (Critical / High / Medium / Low)
- What is wrong
- Why it matters
- How to fix it

If a finding comes from team memory, start that finding with the exact tag [MEMORY].
Do not invent team rules that are not present in the memory.

End the review with a section titled "## Suggested Fix" containing one
corrected version of the code in a single fenced {language} code block.

FORMAT RULE: the very first line of your answer must be exactly
SCORE: <integer 0-100>
where the score is the overall quality of the submitted code (100 = flawless).
Then continue with the structured review.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": f"You are an expert {language} code reviewer."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


def extract_learning(code, review, language="Python"):
    prompt = f"""
You are maintaining the long-term engineering memory of a software team.

Your task is to extract ONLY reusable engineering rules from this
code review.

====================
CODE ({language})
====================

{code}

====================
CODE REVIEW
====================

{review}

====================
WHAT TO STORE
====================

Store only lessons that are useful for reviewing FUTURE code.

Good lessons include:

- Team architecture rules
- Explicit coding standards
- Security requirements
- Important design decisions
- Recurring mistakes that should be detected again
- Rules that apply to multiple files or future features

====================
WHAT NOT TO STORE
====================

Do NOT store:

- The complete code
- The complete review
- A description of this specific function
- Specific variable names from this code unless they represent a team rule
- Temporary bugs
- One-time implementation details
- Generic advice such as "write clean code"
- Repeated versions of the same rule
- Severity labels
- Dates
- Names of developers
- Action items specific to this one task

IMPORTANT:

Extract a rule only if it can be reused on a DIFFERENT piece of code.

For example, this is GOOD:

"Controllers must not access the database directly; database operations belong in the Repository layer."

This is BAD:

"The create_order function should move its INSERT statement to OrderRepository."

The first is a reusable team rule.
The second only describes this particular code.

====================
OUTPUT FORMAT
====================

Return 3 to 6 concise standalone rules.

If a rule only applies to {language}, start it with "In {language}, ".
If it applies to any language, do not mention a language.

Each rule must:

- Be one sentence
- Be specific
- Be reusable
- Make sense without seeing this review
- Contain no numbering
- Contain no bullet symbols
- Contain no dates
- Contain no explanations

If two lessons express the same rule, combine them into ONE rule.

Example output:

Controllers must not access the database directly; database operations belong in the Repository layer.

SQL queries must use parameterized statements or an ORM to prevent SQL injection.

HTTP endpoints must validate request payloads before processing user input.

Public functions must include type hints and concise docstrings.

Return ONLY the rules, one per line.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract concise, reusable engineering rules "
                    "for long-term team memory."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content.strip()