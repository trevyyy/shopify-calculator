import os
import streamlit as st
import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from io import StringIO
from zipfile import ZipFile

st.set_page_config(page_icon='🎨')

SHEET_ID = '19VEjnXTDYhZu2Yy7uQzQhKgynLB8DngUokQJupCeMN8'
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
artist_data_full = pd.read_csv(url, on_bad_lines='skip')
artist_data_full['items'] = artist_data_full['items'].apply(lambda x: [n.strip() for n in x.split(';')])


def format_date(date):
    date, _ = date.split('T')
    year, month, day = date.split('-')
    return f'{day}/{month}/{year}'


shopify_file = st.file_uploader('Shopify file', type='csv')
if shopify_file:
    shopify_df = pd.read_csv(shopify_file, usecols=['Date', 'Order', 'Product', 'Variant', 'Gross sales'])
    shopify_df.rename(columns={'Gross sales': 'Sales'}, inplace=True)
    shopify_df.fillna('', inplace=True)
    shopify_df['Size'] = shopify_df['Variant'].apply(lambda n: n.split('/')[0].strip() if '/' in n else n)
    shopify_df['Frame'] = shopify_df['Variant'].apply(lambda n: n.split('/')[1].strip() if '/' in n else n)
    shopify_df['Date'] = shopify_df['Date'].apply(lambda n: format_date(n))
    shopify_df = shopify_df[['Date', 'Order', 'Product', 'Size', 'Frame', 'Sales']]
    st.dataframe(shopify_df, use_container_width=True, height=200)
    st.write('---')

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

    to_pay_list = []
    for artist_name in list(artist_data_full['name']):
        artist_data = artist_data_full[artist_data_full.name == artist_name][['items', 'framed', 'unframed']]
        artist_data = artist_data.reset_index(drop=True)
        artist_data_pretty = artist_data.rename(
            columns={'items': 'Items', 'framed': 'Framed rate', 'unframed': 'Unframed rate'})
        artist_data_pretty['Framed rate'] = artist_data_pretty['Framed rate'].apply(lambda x: f'{x * 100}%')
        artist_data_pretty['Unframed rate'] = artist_data_pretty['Unframed rate'].apply(lambda x: f'{x * 100}%')

        person_df = shopify_df[shopify_df['Product'].isin(artist_data['items'][0])]
        person_df['Percentage'] = [artist_data["unframed"][0] if f == 'Unframed' else artist_data["framed"][0] for f in person_df['Frame']]
        person_df['Cut'] = person_df['Sales'] * person_df['Percentage']
        if (size := len(person_df)) > 0:
            total = person_df['Cut'].sum()
            total_col = [round(total, 2)] + ([''] * (size - 1))
            person_df['Total'] = total_col
        else:
            person_df['Total'] = []

        to_pay_list.append((artist_name, round(person_df['Cut'].sum(), 2)))

        with ZipFile('tmp.zip', 'a') as zf:
            s = StringIO()
            person_df.to_csv(s, index=False, header=True)
            zf.writestr(f'{artist_name} {datetime.today().strftime("%d-%m-%Y")}.csv', s.getvalue())

    df = pd.DataFrame(to_pay_list, columns=['Artist', 'Total'])
    st.dataframe(df)
    st.write(f':red[Total: £{round(sum([i[1] for i in to_pay_list]), 2)}]')

    with open("tmp.zip", "rb") as fp:
        btn = st.download_button(
            label="Download ZIP",
            data=fp,
            file_name=f'Artist commissions {datetime.today().strftime("%d-%m-%Y")}.zip',
            mime="application/zip"
        )
    os.remove("tmp.zip")
