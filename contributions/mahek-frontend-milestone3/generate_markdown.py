import os
import sys

from report_content import (
    METADATA, CERTIFICATE_TEXT, ACKNOWLEDGEMENT_TEXT, ABSTRACT_TEXT,
    CHAPTER_6_TEXT, CHAPTER_7_TEXT, CHAPTER_8_TEXT, CHAPTER_9_TEXT,
    CHAPTER_10_TEXT, CHAPTER_11_TEXT, CHAPTER_12_TEXT
)
from report_content_part2 import (
    CHAPTER_13_TEXT, CHAPTER_14_TEXT, CHAPTER_15_TEXT, CHAPTER_16_TEXT,
    CHAPTER_17_TEXT, CHAPTER_18_TEXT, CHAPTER_19_TEXT, CHAPTER_20_TEXT,
    CHAPTER_21_TEXT, CHAPTER_22_TEXT, DAYWISE_SCHEDULE_ROWS
)
from report_content_part3 import (
    CHAPTER_23_TEXT, CHAPTER_24_TEXT, CHAPTER_25_TEXT, CHAPTER_26_TEXT,
    CHAPTER_27_TEXT
)

def build_markdown():
    md = []
    
    # Title & Metadata
    md.append(f"# {METADATA['project_name'].upper()}")
    md.append(f"### Technical Internship Report — Frontend Engineering & Architectural Implementation")
    md.append(f"**Application Code Name:** {METADATA['project_code_name']}  ")
    md.append(f"**Organization:** {METADATA['organization']}  ")
    md.append(f"**Program:** {METADATA['internship_program']}  ")
    md.append(f"**Team:** {METADATA['team']}  ")
    md.append(f"**My Role:** {METADATA['role']}  ")
    md.append(f"**Student Name:** {METADATA['student_name']}  ")
    md.append(f"**Date:** {METADATA['submission_date']}  ")
    md.append("\n---\n")

    # Chapter 1: Cover Page
    md.append("# Chapter 1: Cover Page")
    md.append(f"""
| Attribute | Detail |
| :--- | :--- |
| **Project Title** | {METADATA['project_name']} ({METADATA['project_code_name']}) |
| **Organization** | {METADATA['organization']} |
| **Internship Track** | Full-Stack AI & Autonomous Systems |
| **Assigned Squad** | {METADATA['team']} |
| **Designated Role** | {METADATA['role']} |
| **Student Engineer** | {METADATA['student_name']} |
| **Mentor / Evaluator** | {METADATA['mentor_name']} |
| **Department** | {METADATA['college_name']} |
| **Academic Year** | {METADATA['academic_year']} |
| **Submission Period** | {METADATA['submission_date']} |
""")
    md.append("\n---\n")

    # Chapter 2: Certificate Page
    md.append("# Chapter 2: Certificate Page (Placeholder)")
    md.append(CERTIFICATE_TEXT.strip())
    md.append("""
\n**Certification Endorsement Signatures:**\n
| Designation | Name | Signature & Date |
| :--- | :--- | :--- |
| **Student Developer** | Mahek Saba Shaikh (Team C) | _____________________ |
| **Industry Mentor** | Technical Lead, Infosys Springboard | _____________________ |
| **Project Coordinator** | Internship Evaluation Committee | _____________________ |
| **Department Head** | Computer Science & Engineering | _____________________ |
""")
    md.append("\n---\n")

    # Chapter 3: Acknowledgement
    md.append("# Chapter 3: Acknowledgement")
    md.append(ACKNOWLEDGEMENT_TEXT.strip())
    md.append("\n---\n")

    # Chapter 4: Abstract
    md.append("# Chapter 4: Abstract")
    md.append(ABSTRACT_TEXT.strip())
    md.append("\n---\n")

    # Chapter 5: Table of Contents
    md.append("# Chapter 5: Table of Contents")
    toc_items = [
        "1. Cover Page",
        "2. Certificate Page (Placeholder)",
        "3. Acknowledgement",
        "4. Abstract",
        "5. Table of Contents",
        "6. Introduction to Infosys Springboard Internship",
        "7. Project Overview",
        "8. Problem Statement",
        "9. Project Objectives",
        "10. Technologies and Tools Used",
        "11. Frontend Architecture and Project Structure",
        "12. My Role and Responsibilities",
        "13. Detailed Frontend Module Implementation",
        "14. Leads Dashboard Implementation",
        "15. Lead Intelligence Dashboard Implementation",
        "16. Outreach Interface Implementation",
        "17. AI Email Generator Implementation",
        "18. Lead Scoring and Outreach Recommendations",
        "19. Frontend and Backend API Integration",
        "20. UI Testing and Validation",
        "21. Challenges Faced and Solutions",
        "22. Day-wise and Milestone-wise Progress (40-Day SDLC Schedule)",
        "23. Screenshots of Actual Project UI",
        "24. Skills and Learning Outcomes",
        "25. Conclusion",
        "26. Future Enhancements",
        "27. References"
    ]
    for item in toc_items:
        md.append(f"- **{item}**")
    md.append("\n---\n")

    # Chapters 6 to 12
    md.append("# Chapter 6: Introduction to Infosys Springboard Internship")
    md.append(CHAPTER_6_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 7: Project Overview")
    md.append(CHAPTER_7_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 8: Problem Statement")
    md.append(CHAPTER_8_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 9: Project Objectives")
    md.append(CHAPTER_9_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 10: Technologies and Tools Used")
    md.append(CHAPTER_10_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 11: Frontend Architecture and Project Structure")
    md.append(CHAPTER_11_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 12: My Role and Responsibilities")
    md.append(CHAPTER_12_TEXT.strip())
    md.append("\n---\n")

    # Chapters 13 to 22
    md.append("# Chapter 13: Detailed Frontend Module Implementation")
    md.append(CHAPTER_13_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 14: Leads Dashboard Implementation")
    md.append(CHAPTER_14_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 15: Lead Intelligence Dashboard Implementation")
    md.append(CHAPTER_15_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 16: Outreach Interface Implementation")
    md.append(CHAPTER_16_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 17: AI Email Generator Implementation")
    md.append(CHAPTER_17_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 18: Lead Scoring and Outreach Recommendations")
    md.append(CHAPTER_18_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 19: Frontend and Backend API Integration")
    md.append(CHAPTER_19_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 20: UI Testing and Validation")
    md.append(CHAPTER_20_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 21: Challenges Faced and Solutions")
    md.append(CHAPTER_21_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 22: Day-wise and Milestone-wise Progress (40-Day SDLC Schedule)")
    md.append(CHAPTER_22_TEXT.strip())
    md.append("\n| Timeline | Milestone | Frontend Task Description | Status |")
    md.append("| :--- | :--- | :--- | :--- |")
    for day, ms, desc, st in DAYWISE_SCHEDULE_ROWS:
        badge = f"**{st}**"
        md.append(f"| {day} | {ms} | {desc} | {badge} |")
    md.append("\n---\n")

    # Chapters 23 to 27
    md.append("# Chapter 23: Screenshots of Actual Project UI")
    md.append(CHAPTER_23_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 24: Skills and Learning Outcomes")
    md.append(CHAPTER_24_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 25: Conclusion")
    md.append(CHAPTER_25_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 26: Future Enhancements")
    md.append(CHAPTER_26_TEXT.strip())
    md.append("\n---\n")

    md.append("# Chapter 27: References")
    md.append(CHAPTER_27_TEXT.strip())
    md.append("\n")

    output_path = os.path.abspath("Internship_Report/INTERNSHIP_TECHNICAL_REPORT.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(md))
    print(f"Generated Markdown report at: {output_path} (size: {os.path.getsize(output_path)} bytes)")

if __name__ == "__main__":
    build_markdown()

