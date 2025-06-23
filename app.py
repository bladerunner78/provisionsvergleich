
from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from fpdf import FPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/vergleichen', methods=['POST'])
def vergleichen():
    try:
        ennux_file = request.files['ennux']
        newsales_file = request.files['newsales']

        ennux_df = pd.read_csv(ennux_file, sep=';')
        newsales_df = pd.read_csv(newsales_file, sep=';')

        expected_columns = ['Versorger', 'Tarif', 'Tarif-ID', 'Starte', 'Typ', 
                            'Verbrauch von', 'Verbrauch bis', 'Provision in Euro']

        for df in [ennux_df, newsales_df]:
            if not all(col in df.columns for col in expected_columns):
                raise ValueError("Eine der Dateien enthält nicht alle erforderlichen Spalten.")

        if 'Sonderprovision' not in ennux_df.columns:
            ennux_df['Sonderprovision'] = 0

        if 'Sonderprovision' not in newsales_df.columns:
            newsales_df['Sonderprovision'] = 0

        ennux_df['Provision in Euro'] = pd.to_numeric(ennux_df['Provision in Euro'], errors='coerce').fillna(0)
        ennux_df['Sonderprovision'] = pd.to_numeric(ennux_df['Sonderprovision'], errors='coerce').fillna(0)
        ennux_df['Provision Gesamt'] = ennux_df['Provision in Euro'] + ennux_df['Sonderprovision']

        newsales_df['Provision in Euro'] = pd.to_numeric(newsales_df['Provision in Euro'], errors='coerce').fillna(0)
        newsales_df['Sonderprovision'] = pd.to_numeric(newsales_df['Sonderprovision'], errors='coerce').fillna(0)
        newsales_df['Provision Gesamt'] = newsales_df['Provision in Euro'] + newsales_df['Sonderprovision']

        ennux_df.columns = newsales_df.columns = ['Versorger', 'Tarif', 'Tarif_ID', 'Starte', 'Typ',
                                                  'Verbrauch_von', 'Verbrauch_bis', 'Provision', 'Sonderprovision', 'Provision_Gesamt']

        merged = pd.merge(
            ennux_df,
            newsales_df,
            on=['Versorger', 'Tarif', 'Tarif_ID', 'Starte', 'Typ', 'Verbrauch_von', 'Verbrauch_bis'],
            suffixes=('_Ennux', '_Newsales24')
        )

        merged['Ergebnis'] = merged[['Provision_Gesamt_Ennux', 'Provision_Gesamt_Newsales24']].max(axis=1)

        class PDF(FPDF):
            def __init__(self):
                super().__init__('L', 'mm', 'A4')
                self.set_auto_page_break(auto=True, margin=10)

            def header(self):
                self.set_font("Arial", "B", 10)
                self.cell(0, 10, "Provisionsvergleich Ennux vs. Newsales24", ln=1, align="C")

            def row(self, data, highlight_index=None):
                self.set_font("Arial", "", 6)
                for i, item in enumerate(data):
                    if highlight_index is not None and i == highlight_index:
                        self.set_fill_color(255, 255, 0)
                        self.cell(35, 6, str(item), border=1, ln=0, fill=True)
                    else:
                        self.cell(35, 6, str(item), border=1, ln=0)
                self.ln()

        pdf = PDF()
        pdf.add_page()

        columns = ['Versorger', 'Tarif', 'Tarif_ID', 'Starte', 'Typ', 'Verbrauch_von', 'Verbrauch_bis',
                   'Provision_Gesamt_Ennux', 'Provision_Gesamt_Newsales24', 'Ergebnis']

        pdf.set_font("Arial", "B", 6)
        for col in columns:
            pdf.cell(35, 6, col, border=1)
        pdf.ln()

        for _, row in merged.iterrows():
            row_list = [row[col] for col in columns]
            highlight = 9 if row['Ergebnis'] == row['Provision_Gesamt_Newsales24'] else None
            pdf.row(row_list, highlight_index=highlight)

        output_path = os.path.join(OUTPUT_FOLDER, 'provisionen_vergleich.pdf')
        pdf.output(output_path)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return render_template('index.html', error=str(e))

if __name__ == '__main__':
    app.run()
