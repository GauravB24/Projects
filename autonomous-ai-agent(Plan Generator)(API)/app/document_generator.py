import re
from datetime import datetime
from pathlib import Path

from docx import Document


class DocumentGenerator:

    def generate(self, content: str):

        document = Document()

        for line in content.splitlines():

            line = line.strip()

            if not line:
                continue

            if line.startswith("# "):

                document.add_heading(
                    line[2:].strip(),
                    level=1
                )

            elif line.startswith("## "):

                document.add_heading(
                    line[3:].strip(),
                    level=2
                )

            elif line.startswith("### "):

                document.add_heading(
                    line[4:].strip(),
                    level=3
                )

            elif line.startswith("- "):

                paragraph = document.add_paragraph(
                    style="List Bullet"
                )

                self._add_formatted_text(
                    paragraph,
                    line[2:].strip()
                )

            elif re.match(r"^\d+\.\s+", line):

                text = re.sub(
                    r"^\d+\.\s+",
                    "",
                    line
                )

                paragraph = document.add_paragraph(
                    style="List Number"
                )

                self._add_formatted_text(
                    paragraph,
                    text
                )

            else:

                paragraph = document.add_paragraph()

                self._add_formatted_text(
                    paragraph,
                    line
                )

        output_folder = Path("output")
        output_folder.mkdir(exist_ok=True)

        filename = datetime.now().strftime(
            "generated_document_%Y%m%d_%H%M%S.docx"
        )

        output_file = output_folder / filename

        document.save(output_file)

        return str(output_file)

    def _add_formatted_text(self, paragraph, text):

        parts = re.split(r"(\*\*.*?\*\*)", text)

        for part in parts:

            if not part:
                continue

            if part.startswith("**") and part.endswith("**"):

                run = paragraph.add_run(
                    part[2:-2]
                )

                run.bold = True

            else:

                paragraph.add_run(part)