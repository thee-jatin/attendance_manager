from weasyprint import HTML

html_content = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: Arial, sans-serif; margin: 30px; line-height: 1.6; color: #333; }
    h1 { text-align: center; color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 8px; }
    h2 { color: #2c5282; margin-top: 25px; border-bottom: 1px solid #cbd5e0; padding-bottom: 4px; }
    h3 { color: #2b6cb0; margin-top: 15px; }
    ul { margin-top: 5px; }
    li { margin-bottom: 5px; }
    pre { background: #f7fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 5px; font-family: monospace; white-space: pre-wrap; }
</style>
</head>
<body>

<h1>Soft Skills Assignment</h1>

<h2>Q1. Process of Writing an Effective CV and Resume with Format</h2>

<h3>1. Key Differences</h3>
<ul>
    <li><b>Resume:</b> 1–2 pages long, concise, tailored specifically for a target job role.</li>
    <li><b>CV (Curriculum Vitae):</b> 2+ pages long, detailed academic history, research, and publications.</li>
</ul>

<h3>2. Process of Writing</h3>
<ol>
    <li><b>Analyze Job Role:</b> Tailor content and skills according to the job description.</li>
    <li><b>Layout & Formatting:</b> Use clean fonts (10-12pt), 1-inch margins, and logical headings.</li>
    <li><b>Core Sections:</b>
        <ul>
            <li><b>Header:</b> Contact Info, LinkedIn/GitHub links.</li>
            <li><b>Summary:</b> 2-line elevator pitch highlighting technical skills.</li>
            <li><b>Education:</b> Degree, College name, Year, Marks/CGPA.</li>
            <li><b>Skills:</b> Technical languages, tools, and soft skills.</li>
            <li><b>Projects/Experience:</b> Key achievements using action verbs.</li>
            <li><b>Certifications:</b> Relevant courses and honors.</li>
        </ul>
    </li>
    <li><b>ATS Optimization:</b> Use exact keywords from the job listing.</li>
    <li><b>Proofread:</b> Check for grammar, alignment, and spelling errors.</li>
</ol>

<h3>3. Standard Resume Format</h3>
<pre>
================================================================================
                                 [YOUR NAME]
                 Aligarh, UP | +91-XXXXXXXXXX | email@example.com
                      LinkedIn: linkedin.com/in/username
================================================================================

PROFESSIONAL SUMMARY
--------------------
Motivated B.Tech CSE student proficient in Python, Data Structures, and Web 
Development, seeking software engineering opportunities.

EDUCATION
---------
B.Tech in Computer Science Engineering                          2024 – 2028
SSLD Varshney Engineering College, Aligarh | CGPA: X.X

TECHNICAL SKILLS
----------------
* Languages: C, C++, Python
* Web/Tools: HTML, CSS, JavaScript, Git, VS Code
* Fundamentals: Data Structures, OOPs, DBMS

PROJECTS
--------
1. Project Title | Tech Used
   * Developed feature X improving system performance by Y%.
   * Designed responsive UI and integrated database logic.

CERTIFICATIONS
--------------
* Certification Name 1 – Platform/Institute
================================================================================
</pre>

<h2>Q2. Interview Skills & Group Discussion (GD) Techniques</h2>

<h3>1. Interview Skills</h3>
<ul>
    <li><b>Pre-Interview:</b>
        <ul>
            <li>Research company products, tech stack, and values.</li>
            <li>Be ready to explain every project and skill listed in the resume.</li>
            <li>Prepare STAR method (Situation, Task, Action, Result) for situational questions.</li>
        </ul>
    </li>
    <li><b>During Interview:</b>
        <ul>
            <li>Keep professional body language, good posture, and eye contact.</li>
            <li>Listen carefully before answering; clarify questions if confused.</li>
            <li>Be honest—admit politely if an answer is unknown instead of guessing.</li>
        </ul>
    </li>
    <li><b>Post-Interview:</b>
        <ul>
            <li>Ask 1-2 thoughtful questions about the role or team.</li>
        </ul>
    </li>
</ul>

<h3>2. Group Discussion (GD) Techniques</h3>
<ul>
    <li><b>Do's:</b>
        <ul>
            <li><b>Initiate:</b> Start only if knowledgeable about the topic to frame the context.</li>
            <li><b>Content Quality:</b> State facts, examples, and structured thoughts over raw volume.</li>
            <li><b>Active Listening:</b> Agree/build on others' points ("Adding to what my peer said...").</li>
            <li><b>Body Language:</b> Open posture, addressing the entire group (not just the examiner).</li>
            <li><b>Summarize:</b> Offer a balanced summary if the group hasn't reached a conclusion.</li>
        </ul>
    </li>
    <li><b>Don'ts:</b>
        <ul>
            <li>Do not interrupt others aggressively or create a fish-market scenario.</li>
            <li>Avoid speaking off-topic or using slang.</li>
            <li>Avoid dominating the full duration; let quiet members speak.</li>
        </ul>
    </li>
</ul>

</body>
</html>
"""

# HTML content ko PDF me write kar dega
with open("assignment.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML file generated! Open 'assignment.html' in Chrome and press Ctrl+P to Save as PDF.")