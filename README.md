# Rugby Match Analytics and Reporting Tools

This repository contains Python scripts developed to assist in statistical analysis for a Major League Rugby (MLR) team. These tools were used during the season to analyze XML match event data and Excel-based league stats, producing weekly reports and visual presentations on opposing teams.

## 🏉 Project Overview

The MLR league provided XML files describing all events in each rugby game. This project includes two primary tools:

1. **Match Event Analyzer** (StatMonkey.py)  
   Parses XML game files to extract meaningful statistics, generates visualizations with `matplotlib`, and inserts them directly into PowerPoint reports using `python-pptx`.

2. **Team Comparison** (Team_Report.py)  
   Reads Excel sheets containing comprehensive league-wide stats. For each upcoming opponent, it identifies statistical strengths and weaknesses relative to the league and generates a presentation summarizing key insights.

These tools automated the weekly reporting process, saving time and improving the quality of tactical insights delivered to coaches and analysts.

## ⚙️ Technologies Used

- **Python** (Data parsing, analysis, automation)
- **pandas** (Excel data processing)
- **matplotlib** (Graphing and visualizations)
- **python-pptx** (Automated PowerPoint generation)
- **lxml / ElementTree** (XML parsing)

## 📸 Sample Output

### **StatMonkey.py**

XML Sample

<img src="assets/read-me-assets/sample-xml.png" alt="XML Sample" width="300"/>

Results

<img src="assets/read-me-assets/stat-monkey-1.png" alt="Sample Stat Monkey Result" width="500"/>
<img src="assets/read-me-assets/stat-monkey-2.png" alt="Sample Stat Monkey Result" width="500"/>
<img src="assets/read-me-assets/stat-monkey-3.png" alt="Sample Stat Monkey Result" width="500"/>

### **Team_Report.py**

Excel Sample

<img src="assets/read-me-assets/excel-sample.png" alt="Excel Sample" width="300"/>

Results

<img src="assets/read-me-assets/team-report-1.png" alt="Sample Team Report Result" width="500"/>
<img src="assets/read-me-assets/team-report-2.png" alt="Sample Team Report Result" width="500"/>

## Acknowledgments
- Oval Insights and Major League Rugby for providing the match event XML files
- Coaching and analyst staff for weekly feedback

