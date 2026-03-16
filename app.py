from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'cattle_app_secret_key_2024'

DATA_FILE = 'cattle_treatments.json'


# -------------------------
# DATA HELPERS
# -------------------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def save_treatment(herd, tag_number, medicine, notes):
    data = load_data()

    if herd not in data:
        data[herd] = []

    new_treatment = {
        "id": len(data[herd]) + 1,
        "tag_number": tag_number,
        "medicine": medicine,
        "notes": notes,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    data[herd].append(new_treatment)
    save_data(data)


def update_treatment(herd, treatment_id, tag_number, medicine, notes):
    data = load_data()

    for t in data.get(herd, []):
        if t["id"] == treatment_id:
            t["tag_number"] = tag_number
            t["medicine"] = medicine
            t["notes"] = notes
            t["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    save_data(data)


# -------------------------
# ROUTES
# -------------------------

@app.route('/select-herd', methods=['GET', 'POST'])
def select_herd():
    data = load_data()
    herds = list(data.keys())

    if request.method == 'POST':
        existing = request.form.get('existing_herd', '').strip()
        new = request.form.get('new_herd', '').strip()

        herd = new if new else existing

        if herd:
            session.clear()
            session['herd'] = herd
            return redirect(url_for('index'))

    return render_template('select_herd.html', herds=herds)

@app.route('/')
def index():
    if 'herd' not in session:
        return redirect(url_for('select_herd'))

    data = load_data()
    herd = session['herd']
    treatments = data.get(herd, [])

    return render_template(
        'index.html',
        herd=herd,
        treatments=treatments
    )


@app.route('/step1')
def step1():
    if 'herd' not in session:
        return redirect(url_for('select_herd'))
    
    # Clear medicines list when starting new treatment
    if 'medicines' in session:
        session.pop('medicines')

    return render_template('step1_tag.html', herd=session['herd'])


@app.route('/step2', methods=['POST'])
def step2():
    tag_number = request.form.get('tag_number', '').strip()

    if not tag_number:
        return redirect(url_for('step1'))

    session['tag_number'] = tag_number
    return render_template(
        'step2_medicine.html',
        tag_number=tag_number,
        herd=session['herd']
    )


@app.route('/step3', methods=['POST'])
def step3():
    medicine_type = request.form.get('medicine_type', '').strip()
    add_another = request.form.get('add_another', '')
    
    # Get the medicine based on type
    if medicine_type == 'LA-200':
        medicine = request.form.get('la200_dosage', '').strip()
    elif medicine_type == 'other':
        medicine = request.form.get('other_medicine', '').strip()
    else:
        return redirect(url_for('step1'))
    
    if not medicine:
        return redirect(url_for('step2'))
    
    # Initialize medicines list if not exists
    if 'medicines' not in session:
        session['medicines'] = []
    
    # Add this medicine to the list
    session['medicines'].append(medicine)
    session.modified = True
    
    # If user wants to add another medication, go back to step2
    if add_another == 'yes':
        return render_template(
            'step2_medicine.html',
            tag_number=session['tag_number'],
            herd=session['herd']
        )
    else:
        # Combine all medicines into one string
        session['medicine'] = ', '.join(session['medicines'])
        
        # Proceed to notes
        return render_template(
            'step3_notes.html',
            herd=session['herd'],
            tag_number=session['tag_number'],
            medicine=session['medicine']
        )


@app.route('/summary', methods=['POST'])
def summary():
    notes = request.form.get('notes', '').strip()
    herd = session['herd']

    if 'edit_id' in session:
        update_treatment(
            herd,
            session['edit_id'],
            session['tag_number'],
            session['medicine'],
            notes
        )
        session.pop('edit_id')
    else:
        save_treatment(
            herd,
            session['tag_number'],
            session['medicine'],
            notes
        )
    
    # Clear medicines list for next treatment
    if 'medicines' in session:
        session.pop('medicines')

    return redirect(url_for('index'))


@app.route('/edit/<int:treatment_id>')
def edit(treatment_id):
    herd = session.get('herd')
    data = load_data()

    treatment = next(
        (t for t in data.get(herd, []) if t["id"] == treatment_id),
        None
    )

    if not treatment:
        return redirect(url_for('index'))

    session['edit_id'] = treatment_id
    session['tag_number'] = treatment['tag_number']
    session['medicine'] = treatment['medicine']

    return render_template(
        'step1_tag.html',
        herd=herd,
        tag_number=treatment['tag_number'],
        is_edit=True
    )


@app.route('/delete/<int:treatment_id>', methods=['POST'])
def delete(treatment_id):
    herd = session.get('herd')
    data = load_data()

    data[herd] = [t for t in data.get(herd, []) if t["id"] != treatment_id]
    save_data(data)

    return redirect(url_for('index'))


@app.route('/switch-herd')
def switch_herd():
    session.clear()
    return redirect(url_for('select_herd'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)