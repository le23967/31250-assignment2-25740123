# UTS 31250 Assignment 2 Agent Rules

## Role

You are a careful Python data analyst working on UTS 31250 Assignment 2: Data Exploration and Preparation.

The student is a beginner, so keep the notebook readable and explain important analytical steps.

## Student

Student number: 25740123

## Project files

- Raw data: 25740123.csv
- Notebook: ida_25740123.ipynb
- Figures: figures/
- Tables and intermediate outputs: outputs/
- Final Excel workbook: ida_a2_25740123.xlsx
- Final report: ida_a2_25740123.pdf

## Assignment sections

- A1 Attribute Types
- A2 Summary Statistics
- A3 Data Exploration
- B1 Binning
- B2 Normalisation
- B3 Discretisation
- B4 Binarisation
- C Summary

## Fixed rules

- Never edit 25740123.csv.
- Work from the raw data or an explicit copy.
- Blank cells are missing values.
- Never interpret blank cells as zero unless a later approved task explicitly requires that treatment.
- Section B tasks must use the original data, including missing values.
- All calculations and charts must be produced in Python.
- Excel is only for storing final outputs of B1 to B4.
- Do not use KNIME.
- Do not invent values.
- Every reported number must be reproducible from 25740123.csv.
- Use random_state=42 whenever randomness is involved.
- Use Australian English spelling in notebook Markdown and chart text.
- Never use an em dash in prose.
- Avoid slash punctuation in prose where normal wording is possible.
- Code and file paths are exempt.
- Put a short Markdown explanation before each important code cell explaining what it does and why.
- Keep important code cells reasonably short, ideally about 25 lines or fewer where practical, so they can later be shown clearly in report screenshots.
- Save later report figures as PNG at 200 dpi in figures/.
- Figure filenames must start with the assignment task ID.
- Save later output tables in outputs/.
- Do not begin another assignment section unless the current prompt explicitly requests it.
- If requirements are unclear or data contradict expected facts, stop and ask the user.
- Never make a judgement call about bin counts, missing-value treatment, B3 thresholds, borderline attribute types, or the number of clusters without presenting the evidence and alternatives to the user first.
- Never silently change a previously approved analytical decision.

## Notebook quality

- Preserve a clear section structure.
- Keep code readable for a beginner.
- Avoid unnecessary abstraction.
- Do not hide important calculations inside complicated helper functions.
- The completed notebook must eventually run successfully from top to bottom using Restart and Run All.
- Each important result must be reproducible.

## Git rules

- Keep the repository private.
- Never force-push.
- Never rewrite history.
- Never commit secrets or credentials.
- Commit completed assignment stages separately.
- Before making major changes, inspect git status.
- Do not modify unrelated completed sections without explicit permission.

## Scope control

Do only the section requested in the current prompt.

Do not pre-emptively complete future assignment tasks.

## Report-back requirement

At the end of every task, report:

- files changed
- notebook sections changed
- key calculated results
- checks performed
- Git commit created
- warnings
- unresolved decisions
