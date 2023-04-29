import streamlit as st
import json
import time
import string
import random

if 'artists' not in st.session_state:
    with open('artists.json') as j:
        st.session_state['artists'] = json.load(j)


def generate_random_string():
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(16))


new_data = []

if st.button('➕ Add'):
    st.session_state['artists'].append({'name': '', 'items': '', 'unframed': 0.1, 'framed': 0.1})

for i, a in enumerate(st.session_state['artists']):
    name = st.text_input('Name', value=a['name'], key=f'0-{i}-{a}')
    items = st.text_area('Prints', value='\n'.join(a['items']), help='Add each print on a new line', key=f'1-{i}-{a}')
    col1, col2, _, _ = st.columns(4)
    framed = col1.number_input('Framed rate', value=a['framed'], max_value=1.0, k=generate_random_string())
    col1.caption(f'{framed:.0%}')
    unframed = col2.number_input('Unframed rate', value=a['unframed'], max_value=1.0, k=generate_random_string())
    col2.caption(f'{unframed:.0%}')
    new_data.append({'name': name, 'items': [i.strip() for i in items.splitlines() if i.strip()],
                     'framed': framed, 'unframed': unframed})
    st.write('---')

if st.button('Save'):
    new_data = [n for n in new_data if n['name']]
    with open('artists.json', 'w') as j:
        json.dump(new_data, j)
    st.success('Saved')
    with open('artists.json') as j:
        st.session_state['artists'] = json.load(j)
    time.sleep(2)
    st.experimental_rerun()
