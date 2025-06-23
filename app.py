from flask import Flask, render_template, request, send_from_directory
import pandas as pd
from fpdf import FPDF
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vergleichen', methods=['POST'])
def vergleichen():
    ennux_file = request.files['ennux']
    newsales_file = request.files['newsales']

    ennux_path = os.path.join(UPLOAD_FOLDER, 'Ennux.csv')
    newsales_path = os.path.join(UPLOAD_FOLDER, 'Newsales.csv')
    ennux_file.save(ennux_path)
    newsales_file.save(newsales_path)

    ennux = pd.read_csv(ennux_path, sep=';', encoding='utf-8')
    newsales = pd.read_csv(newsales_path, sep=';', encoding='utf-8')

    ennux['Gesamtprovision'] = pd.to_numeric(ennux['Provision in Euro'], errors='coerce') + pd.to_numeric(ennux['Sonderprovision'], errors='coerce')
    newsales['Gesamtprovision'] = pd.to_numeric(newsales['Provision in Euro'], errors='coerce') + pd.to_numeric(newsales['Sonderprovision'], errors='coerce')

    spalten = ['Versorger', 'Tarif', 'Tarif-ID', 'Starte', 'Typ', 'Verbrauch von', 'Verbrauch bis', 'Gesamtprovision']
    ennux = ennux[spalten].copy()
    newsales = newsales[spalten].copy()
    ennux['Quelle'] = 'Ennux'
    newsales['Quelle'] = 'Newsales24'

    combined = pd.concat([ennux, newsales], ignore_index=True)
    grouped = combined.groupby(
        ['Versorger', 'Tarif', 'Tarif-ID', 'Starte', 'Typ', 'Verbrauch von', 'Verbrauch bis'],
        as_index=False
    ).apply(lambda g: g.loc[g['Gesamtprovision'].idxmax()]).reset_index(drop=True)

    pdf = FPDF('L', 'mm', 'A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, 'Provisionsvergleich inkl. Sonderprovision', ln=1, align='C')

    pdf.set_font('Arial', 'B', 7)
    columns = ['Versorger', 'Tarif', 'Tarif-ID', 'Starte', 'Typ', 'Verbrauch von', 'Verbrauch bis', 'Gesamtprovision']
    for col in columns:
        pdf.cell(35, 6, col, border=1)
    pdf.ln()

    pdf.set_font('Arial', '', 7)
    for _, row in grouped.iterrows():
        for i, col in enumerate(columns):
            if col == 'Gesamtprovision' and row['Quelle'] == 'Newsales24':
                pdf.set_fill_color(255, 255, 0)
                pdf.cell(35, 6, str(row[col]), border=1, fill=True)
            else:
                pdf.cell(35, 6, str(row[col]), border=1)
        pdf.ln()

    output_path = os.path.join(UPLOAD_FOLDER, 'provisionsvergleich.pdf')
    pdf.output(output_path)
    return render_template('index.html', pdf_url='/download/provisionsvergleich.pdf')

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
