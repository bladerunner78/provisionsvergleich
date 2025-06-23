
from flask import Flask, render_template, request, send_file, flash
import pandas as pd
from fpdf import FPDF
import os
import uuid

app = Flask(__name__)
app.secret_key = 'geheim'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vergleichen', methods=['POST'])
def vergleichen():
    try:
        ennux_file = request.files['ennux_file']
        newsales_file = request.files['newsales_file']

        if not ennux_file or not newsales_file:
            flash("Beide Dateien müssen hochgeladen werden.")
            return render_template('index.html')

        ennux = pd.read_csv(ennux_file, sep=';')
        newsales = pd.read_csv(newsales_file, sep=';')

        required_cols = ['Versorger', 'Tarif', 'Tarif-ID', 'Starte', 'Typ', 'Verbrauch von', 'Verbrauch bis', 'Provision in Euro']

        if not all(col in ennux.columns for col in required_cols):
            flash("Ennux-Datei enthält nicht alle erforderlichen Spalten.")
            return render_template('index.html')
        if not all(col in newsales.columns for col in required_cols):
            flash("Newsales-Datei enthält nicht alle erforderlichen Spalten.")
            return render_template('index.html')

        ennux = ennux[required_cols].copy()
        newsales = newsales[required_cols].copy()

        if 'Sonderprovision' in ennux.columns:
            ennux['Sonderprovision'] = pd.to_numeric(ennux['Sonderprovision'], errors='coerce').fillna(0)
        else:
            ennux['Sonderprovision'] = 0

        for df in [ennux, newsales]:
            df.columns = ['Versorger', 'Tarif', 'Tarif_ID', 'Starte', 'Typ', 'Verbrauch_von', 'Verbrauch_bis', 'Provision']
            df['Verbrauch_von'] = pd.to_numeric(df['Verbrauch_von'], errors='coerce')
            df['Verbrauch_bis'] = pd.to_numeric(df['Verbrauch_bis'], errors='coerce')
            df['Provision'] = pd.to_numeric(df['Provision'], errors='coerce')

        ennux['Provision'] = ennux['Provision'] + ennux['Sonderprovision']
        ennux['Quelle'] = 'Ennux'
        newsales['Quelle'] = 'Newsales24'

        merged = pd.merge(
            ennux,
            newsales,
            on=['Versorger', 'Tarif', 'Tarif_ID', 'Starte', 'Typ', 'Verbrauch_von', 'Verbrauch_bis'],
            suffixes=('_Ennux', '_Newsales24')
        )

        merged['Ergebnis'] = merged[['Provision_Ennux', 'Provision_Newsales24']].max(axis=1)

        filename = f"provisionen_{uuid.uuid4().hex[:8]}.pdf"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", size=7)
        col_width = 40
        row_height = 6

        cols = ['Versorger', 'Tarif', 'Tarif_ID', 'Starte', 'Typ', 'Verbrauch_von', 'Verbrauch_bis', 'Provision_Ennux', 'Provision_Newsales24', 'Ergebnis']
        for col in cols:
            pdf.cell(col_width, row_height, str(col), border=1)
        pdf.ln()

        for _, row in merged.iterrows():
            highlight = row['Ergebnis'] == row['Provision_Newsales24']
            for i, col in enumerate(cols):
                if col == 'Ergebnis' and highlight:
                    pdf.set_fill_color(255, 255, 0)
                    pdf.cell(col_width, row_height, str(row[col]), border=1, fill=True)
                else:
                    pdf.cell(col_width, row_height, str(row[col]), border=1)
            pdf.ln()

        pdf.output(filepath)
        return send_file(filepath, as_attachment=True)

    except Exception as e:
        flash(f"Fehler beim Verarbeiten der Dateien: {str(e)}")
        return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
