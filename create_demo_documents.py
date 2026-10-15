# RuleRadar AI - Demo Documents Generator (PDF, DOCX, TXT)
import os
import pymupdf as fitz
from docx import Document as DocxDoc
from docx.shared import Pt, Inches, RGBColor

DEMO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_documents")
os.makedirs(DEMO_DIR, exist_ok=True)

def create_pdf(filename, title, sections):
    filepath = os.path.join(DEMO_DIR, filename)
    doc = fitz.open()
    
    # Page layout
    page = doc.new_page(width=595, height=842) # A4
    y = 50
    margin = 50
    width = 595 - 2 * margin

    # Document Header Title
    page.insert_text((margin, y), title, fontsize=16, fontname="helv", color=(0.1, 0.2, 0.5))
    y += 25
    page.insert_text((margin, y), "Synthetic Demonstration Agreement for RuleRadar AI", fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5))
    y += 15
    page.draw_line(fitz.Point(margin, y), fitz.Point(595 - margin, y), color=(0.8, 0.8, 0.8), width=1)
    y += 20

    for heading, text in sections:
        # Heading
        if y > 750:
            page = doc.new_page(width=595, height=842)
            y = 50

        page.insert_text((margin, y), heading, fontsize=11, fontname="helv", color=(0.15, 0.2, 0.3))
        y += 16

        # Paragraph text wrapped
        rect = fitz.Rect(margin, y, 595 - margin, y + 150)
        rc = page.insert_textbox(rect, text, fontsize=9.5, fontname="helv", color=(0.2, 0.2, 0.2))
        y += 65

    doc.save(filepath)
    doc.close()
    print(f"Generated PDF: {filepath}")

def create_docx(filename, title, sections):
    filepath = os.path.join(DEMO_DIR, filename)
    doc = DocxDoc()
    
    # Title
    t = doc.add_heading(title, level=0)
    sub = doc.add_paragraph("Synthetic Demonstration Document for RuleRadar AI")
    sub.style.font.color.rgb = RGBColor(128, 128, 128)

    for heading, text in sections:
        doc.add_heading(heading, level=1)
        doc.add_paragraph(text)

    doc.save(filepath)
    print(f"Generated DOCX: {filepath}")

def generate_all():
    # 1. Rental Agreement v1
    rental_v1_sections = [
        ("SECTION 1. PARTIES AND PREMISES", 
         "This Residential Lease Agreement ('Agreement') is entered into on January 1, 2026, by and between Apex Property Management ('Landlord') and John Doe ('Tenant'). Landlord leases to Tenant the premises located at 123 Oak Street, Suite 4B, San Francisco, CA 94102."),
        ("SECTION 2. TERM OF LEASE", 
         "The initial term of this Lease shall commence on February 1, 2026, and continue through January 31, 2027. Either party may terminate this agreement at the conclusion of the term by providing at least 30 days' written notice prior to expiration. In the absence of written notice, this agreement shall automatically renew on a month-to-month basis."),
        ("SECTION 3. MONTHLY RENT AND PAYMENT OBLIGATIONS", 
         "Tenant shall pay to Landlord a monthly rent of $1,200.00. Rent is due on the 1st day of each month via electronic transfer or bank check. If rent is not received by the 5th day of the month, Tenant agrees to pay a late fee of $50.00."),
        ("SECTION 4. SECURITY DEPOSIT AND REFUNDS", 
         "Upon execution of this Lease, Tenant shall deposit with Landlord the sum of $2,400.00 as a security deposit. The security deposit shall be held in an escrow account and returned to Tenant within 30 days after full vacancy, less any documented repair deductions."),
        ("SECTION 5. USE OF PREMISES AND RESTRICTIONS", 
         "Tenant shall use the premises exclusively for residential purposes. Tenant shall not sublet or assign the premises without prior written consent of Landlord. No pets shall be permitted without prior written authorization."),
        ("SECTION 6. REPAIRS AND MAINTENANCE DUTIES", 
         "Tenant shall maintain the leased premises in a clean and sanitary condition. Tenant shall promptly notify Landlord in writing of defective fixtures within 48 hours of discovery. Landlord shall perform structural repairs with reasonable diligence."),
        ("SECTION 7. GOVERNING LAW AND JURISDICTION", 
         "This Agreement shall be governed by and construed in accordance with the laws of the State of California. Any disputes arising hereunder shall be submitted to the exclusive jurisdiction of the state courts located in San Francisco County.")
    ]
    create_pdf("Rental_Agreement_v1.pdf", "RESIDENTIAL LEASE AGREEMENT — VERSION 1.0", rental_v1_sections)

    # 2. Rental Agreement v2 (Revised Version)
    rental_v2_sections = [
        ("SECTION 1. PARTIES AND PREMISES", 
         "This Residential Lease Agreement ('Agreement') is entered into on January 1, 2026, by and between Apex Property Management ('Landlord') and John Doe ('Tenant'). Landlord leases to Tenant the premises located at 123 Oak Street, Suite 4B, San Francisco, CA 94102."),
        ("SECTION 2. TERM OF LEASE", 
         "The initial term of this Lease shall commence on February 1, 2026, and continue through January 31, 2027. Either party may terminate this agreement at the conclusion of the term by providing at least 60 days' written notice prior to expiration. In the absence of written notice, this agreement shall automatically renew on a month-to-month basis."),
        ("SECTION 3. MONTHLY RENT AND PAYMENT OBLIGATIONS", 
         "Tenant shall pay to Landlord a monthly rent of $1,450.00. Rent is due on the 1st day of each month via electronic transfer or bank check. If rent is not received by the 5th day of the month, Tenant agrees to pay a late fee of $150.00. Landlord reserves the right to modify rent and rules at any time without prior notice."),
        ("SECTION 4. SECURITY DEPOSIT AND REFUNDS", 
         "Upon execution of this Lease, Tenant shall deposit with Landlord the sum of $2,900.00 as a security deposit. The security deposit shall be held in an escrow account and returned to Tenant within 30 days after full vacancy, less any documented repair deductions."),
        ("SECTION 5. PET POLICY AND USE OF PREMISES", 
         "Tenant is permitted to keep domestic pets subject to reasonable building noise regulations. Tenant shall use the premises exclusively for private residential purposes. Tenant shall not sublet or assign the premises without prior written consent of Landlord."),
        ("SECTION 6. REPAIRS AND MAINTENANCE DUTIES", 
         "Tenant shall maintain the leased premises in a clean and sanitary condition. Tenant shall promptly notify Landlord in writing of defective fixtures within 48 hours of discovery. Landlord shall perform structural repairs with reasonable diligence."),
        ("SECTION 7. GOVERNING LAW AND JURISDICTION", 
         "This Agreement shall be governed by and construed in accordance with the laws of the State of California. Any disputes arising hereunder shall be submitted to the exclusive jurisdiction of the state courts located in San Francisco County.")
    ]
    create_pdf("Rental_Agreement_v2_Revised.pdf", "RESIDENTIAL LEASE AGREEMENT — VERSION 2.0 (REVISED)", rental_v2_sections)

    # 3. Employment Agreement (DOCX & PDF)
    employment_sections = [
        ("SECTION 1. POSITION AND COMMENCEMENT",
         "This Executive Employment Agreement is dated March 1, 2026, between Horizon Technologies Inc. ('Company') and Jane Smith ('Employee'). Employee shall serve as Senior Software Architect commencing on April 1, 2026."),
        ("SECTION 2. COMPENSATION AND SALARY",
         "Company shall pay Employee an annual base salary of $135,000.00, payable in semi-monthly installments in accordance with Company payroll practices. Employee is eligible for a performance bonus of up to 15% of base salary."),
        ("SECTION 3. CONFIDENTIALITY AND PROPRIETARY SECRETS",
         "Employee recognizes that during employment Employee will access confidential information and proprietary algorithms. Employee agrees to maintain strict non-disclosure of confidential information perpetually after termination."),
        ("SECTION 4. INTELLECTUAL PROPERTY AND INVENTIONS",
         "All inventions, software code, patents, and copyrightable works created by Employee during employment shall constitute 'work made for hire' and shall remain the exclusive property of Company."),
        ("SECTION 5. RESTRICTIVE COVENANTS AND NON-COMPETE",
         "During employment and for a period of 2 years following termination, Employee shall not engage in or work for any competing business offering cloud optimization services within North America."),
        ("SECTION 6. TERMINATION AT WILL",
         "Company may terminate this agreement immediately without cause upon written notice. Employee may terminate this agreement by providing at least 30 days' written notice to Company."),
        ("SECTION 7. GOVERNING LAW",
         "This Agreement shall be governed by and construed in accordance with the laws of the State of New York.")
    ]
    create_docx("Employment_Agreement_Executive.docx", "EXECUTIVE EMPLOYMENT AGREEMENT", employment_sections)
    create_pdf("Employment_Agreement_Executive.pdf", "EXECUTIVE EMPLOYMENT AGREEMENT", employment_sections)

    # 4. Freelance Master Services Agreement (PDF)
    freelance_sections = [
        ("SECTION 1. SCOPE OF SERVICES",
         "Contractor agrees to perform artificial intelligence pipeline development, UI integration, and NLP tuning services as specified in Statement of Work #1 executed by Client."),
        ("SECTION 2. PAYMENT TERMS AND INVOICING",
         "Client shall compensate Contractor at the agreed milestone rate of $8,500.00 upon deliverable acceptance. All invoices are payable within 15 days of submission via wire transfer."),
        ("SECTION 3. BROAD INDEMNIFICATION CLAUSE",
         "Contractor agrees to defend, indemnify and hold harmless Client against any and all claims, liabilities, losses, and damages arising out of Contractor's deliverables regardless of fault."),
        ("SECTION 4. OWNERSHIP OF DELIVERABLES",
         "Upon receipt of full payment, all copyright and intellectual property rights in the custom deliverables shall vest exclusively in Client. Contractor retains rights to pre-existing libraries."),
        ("SECTION 5. TERMINATION FOR CONVENIENCE",
         "Either party may terminate this agreement for convenience upon providing 14 days' prior written notice. Client shall pay for all satisfactory work completed prior to termination notice."),
        ("SECTION 6. GOVERNING JURISDICTION",
         "This Agreement is governed by the laws of the State of Washington, with exclusive jurisdiction in King County courts.")
    ]
    create_pdf("Freelance_Consulting_Agreement.pdf", "FREELANCE MASTER SERVICES AGREEMENT", freelance_sections)

    # 5. College Policy Circular (PDF)
    circular_sections = [
        ("SECTION 1. OBJECTIVE AND SCOPE",
         "This Academic Policy Circular #2026/04 applies to all undergraduate and postgraduate students enrolled at the Institute of Technology for the Academic Year 2026-2027."),
        ("SECTION 2. ATTENDANCE REQUIREMENTS AND ELIGIBILITY",
         "Students must maintain a minimum attendance of 75% in all lectures and laboratory sessions to be eligible to appear for the end-semester examinations. Condonation up to 10% requires medical proof."),
        ("SECTION 3. PROJECT SUBMISSION DEADLINE",
         "All capstone project reports and source code repositories must be submitted by November 15, 2026 at 5:00 PM. No extensions shall be granted, and late submissions incur an automatic 20% mark deduction."),
        ("SECTION 4. DISCIPLINARY PENALTIES FOR MISCONDUCT",
         "Any student found engaging in plagiarism or academic dishonesty shall be subject to immediate disciplinary proceedings and may face course failure or suspension."),
        ("SECTION 5. APPEALS AND GRIEVANCE PROCEDURE",
         "Students wishing to appeal an attendance shortfall or grade dispute must file a formal grievance in writing with the Academic Dean within 7 business days of result declaration.")
    ]
    create_pdf("College_Academic_Policy_Circular.pdf", "INSTITUTE OF TECHNOLOGY — ACADEMIC POLICY CIRCULAR", circular_sections)

if __name__ == "__main__":
    generate_all()
