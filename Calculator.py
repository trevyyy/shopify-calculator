import os
import streamlit as st
import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from io import StringIO
from zipfile import ZipFile
from borb.pdf import Document, Alignment
from borb.pdf import Page
from borb.pdf import SingleColumnLayout, MultiColumnLayout
from borb.pdf import Paragraph
from borb.pdf import PDF
from borb.pdf import Image
from borb.pdf import TableCell
from borb.pdf import FlexibleColumnWidthTable
from borb.pdf import Table
from pathlib import Path
from decimal import Decimal
import io
from PIL import Image as PILimage

st.set_page_config(page_icon='🎨')
logo = PILimage.open('logo.png')
st.image(logo)

SHEET_ID = '19VEjnXTDYhZu2Yy7uQzQhKgynLB8DngUokQJupCeMN8'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
artist_data_full = pd.read_csv(url, on_bad_lines='skip')
artist_data_full['items'] = artist_data_full['items'].apply(lambda x: [n.strip() for n in x.split(';')])


def format_date(date):
    date, _ = date.split('T')
    year, month, day = date.split('-')
    return f'{day}/{month}/{year}'


shopify_file = st.file_uploader('Shopify file', type='csv')
if not shopify_file:
    st.session_state['already_run'] = False
    try:
        os.remove("tmp.zip")
    except FileNotFoundError:
        pass
if shopify_file and not st.session_state['already_run']:
    with st.spinner('Making invoices...'):
        shopify_df = pd.read_csv(shopify_file, usecols=['Date', 'Order', 'Product', 'Variant', 'Gross sales'])
        shopify_df.rename(columns={'Gross sales': 'Sales'}, inplace=True)
        shopify_df.fillna('', inplace=True)
        shopify_df['Size'] = shopify_df['Variant'].apply(lambda n: n.split('/')[0].strip() if '/' in n else n)
        shopify_df['Frame'] = shopify_df['Variant'].apply(lambda n: n.split('/')[1].strip() if '/' in n else n)
        shopify_df['Date'] = shopify_df['Date'].apply(lambda n: format_date(n))
        st.session_state['shopify_df'] = shopify_df[['Date', 'Order', 'Product', 'Size', 'Frame', 'Sales']]

        fuzzy_matches = []
        exact_matches = []
        for items in artist_data_full['items']:
            for item in items:
                exact_match_found = False
                temp_matches = []
                for prod in shopify_df['Product'].unique():
                    if prod == item:
                        exact_match_found = True
                        exact_matches.append(prod)
                    elif 90 < fuzz.ratio(item, prod) < 100:
                        temp_matches.append([item, prod])
                if not exact_match_found:
                    fuzzy_matches += temp_matches
        for m in exact_matches:
            for i, f in enumerate(fuzzy_matches):
                if m in f:
                    fuzzy_matches.pop(i)
        if fuzzy_matches:
            for f in fuzzy_matches:
                st.info(f'Check for typos in this product listing: did you mean **"{f[1]}"** instead of **"{f[0]}"**?')

        st.session_state['to_pay_list'] = []
        for artist_name in list(artist_data_full['name']):
            artist_data = artist_data_full[artist_data_full.name == artist_name][['items', 'framed', 'unframed']]
            artist_data = artist_data.reset_index(drop=True)
            artist_data_pretty = artist_data.rename(
                columns={'items': 'Items', 'framed': 'Framed rate', 'unframed': 'Unframed rate'})
            artist_data_pretty['Framed rate'] = artist_data_pretty['Framed rate'].apply(lambda x: f'{x * 100}%')
            artist_data_pretty['Unframed rate'] = artist_data_pretty['Unframed rate'].apply(lambda x: f'{x * 100}%')

            person_df = shopify_df[shopify_df['Product'].isin(artist_data['items'][0])]
            person_df['Percentage'] = [artist_data["unframed"][0] if f == 'Unframed' else artist_data["framed"][0] for f in person_df['Frame']]
            person_df['Cut'] = round(person_df['Sales'] * person_df['Percentage'], 2)
            if (size := len(person_df)) > 0:
                total = person_df['Cut'].sum()
                total_col = [round(total, 2)] + ([''] * (size - 1))
                person_df['Total'] = total_col
            else:
                person_df['Total'] = []

            st.session_state['to_pay_list'].append((artist_name, round(person_df['Cut'].sum(), 2)))

            if person_df.empty:
                continue

            with ZipFile('tmp.zip', 'a') as zf:
                s = StringIO()
                person_df.to_csv(s, index=False, header=True)
                zf.writestr(f'{artist_name} {datetime.today().strftime("%d-%m-%Y")}.csv', s.getvalue())
                # create an empty Document
                pdf = Document()

                # add an empty Page
                page = Page()
                pdf.add_page(page)

                # use a PageLayout (SingleColumnLayout in this case)
                layout = SingleColumnLayout(page)

                # add a Paragraph object
                layout.add(Paragraph("Sales Statement", font='Helvetica-Bold', font_size=Decimal(20)))
                layout.add(Paragraph(datetime.now().strftime('%d %B %Y'), font='Helvetica-Bold', font_size=Decimal(10)))
                months = {
                            1: 'January',
                            2: 'February',
                            3: 'March',
                            4: 'April',
                            5: 'May',
                            6: 'June',
                            7: 'July',
                            8: 'August',
                            9: 'September',
                            10: 'October',
                            11: 'November',
                            12: 'December'
                        }
                month = int(list(person_df['Date'])[0].split('/')[1])
                year = list(person_df['Date'])[0].split('/')[2]
                layout.add(Paragraph(f"Sales For {months.get(month)} {year}", font='Helvetica-Bold', font_size=Decimal(10)))
                layout.add(Paragraph(artist_name, font='Helvetica-Bold', font_size=Decimal(10)))
                layout.add(Paragraph(''))

                table_params = dict(border_top=False,
                                    border_bottom=False,
                                    border_left=False,
                                    border_right=False,
                                    padding_top=Decimal(5),
                                    padding_bottom=Decimal(5),
                                    padding_left=Decimal(10),
                                    padding_right=Decimal(10))
                table = FlexibleColumnWidthTable(number_of_rows=1 + len(person_df), number_of_columns=5)
                table.add(TableCell(Paragraph("Date", font='Helvetica-Bold', font_size=Decimal(10)), **table_params))
                table.add(TableCell(Paragraph("Print", font='Helvetica-Bold', font_size=Decimal(10)), **table_params))
                table.add(TableCell(Paragraph("Size", font='Helvetica-Bold', font_size=Decimal(10)), **table_params))
                table.add(TableCell(Paragraph("Frame", font='Helvetica-Bold', font_size=Decimal(10)), **table_params))
                # table.add(TableCell(Paragraph("Price"), **table_params))
                table.add(TableCell(Paragraph("Commission", font='Helvetica-Bold', font_size=Decimal(10)), **table_params))

                for _, row in person_df.iterrows():
                    for column in ['Date', 'Product', 'Size', 'Frame', 'Cut']:
                        val = str(row[column])
                        if column == 'Cut':
                            if '.' not in val:
                                val += '.00'
                            else:
                                try:
                                    if val[-3] != '.':
                                        val += '0'
                                    else:
                                        pass
                                except IndexError:
                                    pass
                        if column == 'Cut':
                            table.add(TableCell(Paragraph(val, font_size=Decimal(10), horizontal_alignment=Alignment.RIGHT), **table_params))
                        else:
                            table.add(TableCell(Paragraph(val, font_size=Decimal(10)), **table_params))

                layout.add(table)
                layout.add(Paragraph(str(list(person_df['Total'])[0]), font='Helvetica-Bold', font_size=Decimal(10),
                                     horizontal_alignment=Alignment.RIGHT))
                layout.add(Paragraph('All commission is paid out in GBP.', font='Helvetica', font_size=Decimal(10)))
                image_width = 128
                image_length = image_width * 0.3028359375
                layout.add(Image(Path('logo.png'), width=Decimal(image_width), height=Decimal(image_length),
                                 horizontal_alignment=Alignment.RIGHT))

                # store the PDF
                pdf_data = io.BytesIO()
                PDF.dumps(pdf_data, pdf)
                pdf_data.seek(0)

                # Save the PDF into the zip file
                zf.writestr(f'{artist_name} {datetime.today().strftime("%d-%m-%Y")}.pdf', pdf_data.read())

        st.session_state['already_run'] = True

if st.session_state['already_run']:
    st.dataframe(st.session_state['shopify_df'], use_container_width=True, height=200)
    st.write('---')
    df = pd.DataFrame(st.session_state['to_pay_list'], columns=['Artist', 'Total'])
    st.dataframe(df)
    st.write(f':red[Total: £{round(sum([i[1] for i in st.session_state["to_pay_list"]]), 2)}]')
    with open("tmp.zip", "rb") as fp:
        btn = st.download_button(
            label="Download ZIP",
            data=fp,
            file_name=f'Artist commissions {datetime.today().strftime("%d-%m-%Y")}.zip',
            mime="application/zip"
        )
