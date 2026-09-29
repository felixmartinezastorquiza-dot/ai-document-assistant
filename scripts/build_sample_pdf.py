"""Generate the sample price list PDF for the fictional BrightSmile Dental clinic.

Usage:
    python scripts/build_sample_pdf.py
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_docs" / "pricing.pdf"

PRICE_SECTIONS: dict[str, list[tuple[str, str]]] = {
    "Preventive care": [
        ("New patient exam and X-rays", "$120"),
        ("Routine cleaning (adults)", "$95"),
        ("Routine cleaning (children under 12)", "$65"),
        ("Deep cleaning (per quadrant)", "$210"),
    ],
    "Restorative care": [
        ("Tooth-colored filling", "$150 - $250 (depends on size)"),
        ("Porcelain crown", "$1,100"),
        ("Root canal (front tooth)", "$850"),
        ("Root canal (molar)", "$1,200"),
        ("Dental implant (including crown)", "from $3,800"),
    ],
    "Extractions": [
        ("Simple extraction", "$180"),
        ("Surgical extraction", "$350"),
    ],
    "Cosmetic": [
        ("In-office teeth whitening", "$450"),
        ("Take-home whitening kit", "$250"),
    ],
    "Sedation": [
        ("Nitrous oxide", "$75"),
        ("IV sedation (per hour)", "$400"),
    ],
}

NOTES = [
    "Prices are for patients paying without insurance. Your final cost depends on your plan.",
    "Payment plans: treatments over $1,000 can be paid in 12 monthly installments "
    "with 0% interest.",
    "A written estimate is always provided before any treatment begins.",
]


def build_pdf() -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "BrightSmile Dental - Price List 2026", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        0,
        6,
        "Fictional sample company created for a portfolio demo.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    for section, items in PRICE_SECTIONS.items():
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, section, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for treatment, price in items:
            pdf.cell(110, 7, treatment)
            pdf.cell(0, 7, price, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Important notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for note in NOTES:
        pdf.multi_cell(0, 6, f"- {note}", new_x="LMARGIN", new_y="NEXT")

    return pdf


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    build_pdf().output(str(OUTPUT_PATH))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
