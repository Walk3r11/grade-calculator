from flask import Flask, render_template, request, jsonify
import json
import os

app = Flask(__name__)

STORE = os.path.join(os.path.dirname(__file__), 'grades_store.json')

def read_store():
    if not os.path.exists(STORE):
        return []
    try:
        with open(STORE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def write_store(data):
    with open(STORE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_avg(entries):
    if not entries:
        return None
    vals = [float(e['grade']) for e in entries if 'grade' in e]
    if not vals:
        return None
    return sum(vals) / len(vals)


def compute_semester_avg(entries, semester_number):
    if not entries:
        return None
    semester_vals = []
    for e in entries:
        if e.get('type') == 'semester' and int(e.get('semester', 0)) == int(semester_number):
            try:
                semester_vals.append(float(e.get('grade')))
            except Exception:
                continue
    if not semester_vals:
        return None
    return sum(semester_vals) / len(semester_vals)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/grades', methods=['GET'])
def get_grades():
    entries = read_store()
    avg = compute_avg(entries)
    sem1 = compute_semester_avg(entries, 1)
    sem2 = compute_semester_avg(entries, 2)
    return jsonify({
        'entries': entries,
        'average': round(avg, 2) if avg is not None else None,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        }
    })


@app.route('/save-grade', methods=['POST'])
def save_grade():
    data = request.get_json(force=True)
    subject = data.get('subject')
    grade = data.get('grade')
    semester = data.get('semester')
    try:
        grade_val = float(grade)
    except Exception:
        return jsonify({'error': 'invalid grade'}), 400

    if subject is None or grade_val < 2 or grade_val > 6:
        return jsonify({'error': 'invalid payload'}), 400

    semester_num = None
    try:
        if semester is not None:
            semester_num = int(semester)
            if semester_num not in (1, 2):
                semester_num = None
    except Exception:
        semester_num = None

    entries = read_store()
    entry = {'subject': subject, 'grade': grade_val, 'type': 'regular'}
    if semester_num is not None:
        entry['semester'] = semester_num
    entries.append(entry)
    write_store(entries)
    avg = compute_avg(entries)
    return jsonify({'success': True, 'average': round(avg, 2) if avg is not None else None, 'entries': entries})


@app.route('/save-semester-grade', methods=['POST'])
def save_semester_grade():
    data = request.get_json(force=True)
    subject = data.get('subject')
    semester = data.get('semester')
    grade = data.get('grade')
    try:
        grade_val = float(grade)
        semester_num = int(semester)
    except Exception:
        return jsonify({'error': 'invalid payload'}), 400

    if subject is None or semester_num not in (1, 2) or grade_val < 2 or grade_val > 6:
        return jsonify({'error': 'invalid payload'}), 400

    entries = read_store()
    try:
        regular_for_sem = [e for e in entries if e.get('type') == 'regular' and e.get('subject') == subject and int(e.get('semester', -1)) == semester_num]
    except Exception:
        regular_for_sem = []
    if len(regular_for_sem) < 2:
        return jsonify({'error': 'need at least 2 regular grades for this subject and semester'}), 400
    entries.append({'subject': subject, 'grade': grade_val, 'type': 'semester', 'semester': semester_num})
    write_store(entries)
    sem1 = compute_semester_avg(entries, 1)
    sem2 = compute_semester_avg(entries, 2)
    return jsonify({
        'success': True,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        },
        'entries': entries
    })


@app.route('/semester-grades', methods=['GET'])
def get_semester_grades():
    entries = read_store()
    semester_entries = [e for e in entries if e.get('type') == 'semester']
    sem1 = compute_semester_avg(entries, 1)
    sem2 = compute_semester_avg(entries, 2)
    return jsonify({
        'entries': semester_entries,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        }
    })


@app.route('/delete-semester-grades', methods=['POST'])
def delete_semester_grades():
    data = request.get_json(force=True)
    semester = data.get('semester')
    try:
        semester_num = int(semester)
    except Exception:
        return jsonify({'error': 'invalid semester'}), 400
    if semester_num not in (1, 2):
        return jsonify({'error': 'invalid semester'}), 400

    entries = read_store()
    filtered = [e for e in entries if not (e.get('type') == 'semester' and int(e.get('semester', 0)) == semester_num)]
    write_store(filtered)
    sem1 = compute_semester_avg(filtered, 1)
    sem2 = compute_semester_avg(filtered, 2)
    return jsonify({
        'success': True,
        'entries': filtered,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        }
    })


@app.route('/delete-subject-grades', methods=['POST'])
def delete_subject_grades():
    data = request.get_json(force=True)
    subject = data.get('subject')
    semester = data.get('semester')
    if not subject:
        return jsonify({'error': 'subject required'}), 400
    semester_filter = None
    try:
        if semester is not None:
            semester_filter = int(semester)
            if semester_filter not in (1, 2):
                semester_filter = None
    except Exception:
        semester_filter = None

    entries = read_store()
    def should_delete(entry):
        if entry.get('subject') != subject:
            return False
        if semester_filter is None:
            return True
        if entry.get('type') == 'semester':
            return int(entry.get('semester', 0)) == semester_filter
        if entry.get('type') == 'regular':
            try:
                return int(entry.get('semester', -1)) == semester_filter
            except Exception:
                return False
        return False

    filtered = [e for e in entries if not should_delete(e)]
    write_store(filtered)
    sem1 = compute_semester_avg(filtered, 1)
    sem2 = compute_semester_avg(filtered, 2)
    return jsonify({
        'success': True,
        'entries': filtered,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        }
    })


@app.route('/delete-semester-all-grades', methods=['POST'])
def delete_semester_all_grades():
    data = request.get_json(force=True)
    semester = data.get('semester')
    try:
        semester_num = int(semester)
    except Exception:
        return jsonify({'error': 'invalid semester'}), 400
    if semester_num not in (1, 2):
        return jsonify({'error': 'invalid semester'}), 400

    entries = read_store()
    filtered = []
    for e in entries:
        if e.get('type') == 'semester' and int(e.get('semester', 0)) == semester_num:
            continue
        if e.get('type') == 'regular':
            try:
                if int(e.get('semester', -1)) == semester_num:
                    continue
            except Exception:
                pass
        filtered.append(e)
    write_store(filtered)
    sem1 = compute_semester_avg(filtered, 1)
    sem2 = compute_semester_avg(filtered, 2)
    return jsonify({
        'success': True,
        'entries': filtered,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        }
    })


@app.route('/edit-regular-grade', methods=['POST'])
def edit_regular_grade():
    data = request.get_json(force=True)
    subject = data.get('subject')
    semester = data.get('semester')
    new_grade = data.get('grade')
    grade_index = data.get('grade_index')
    if subject is None:
        return jsonify({'error': 'subject required'}), 400
    try:
        semester_num = int(semester)
        if semester_num not in (1, 2):
            return jsonify({'error': 'invalid semester'}), 400
        new_grade_val = float(new_grade)
        if new_grade_val < 2 or new_grade_val > 6:
            return jsonify({'error': 'invalid grade'}), 400
        if grade_index is not None:
            grade_index = int(grade_index)
            if grade_index < 0:
                return jsonify({'error': 'invalid grade index'}), 400
    except Exception:
        return jsonify({'error': 'invalid payload'}), 400

    entries = read_store()
    matching_entries = []
    for idx, e in enumerate(entries):
        if e.get('type') == 'regular' and e.get('subject') == subject and int(e.get('semester', -1)) == semester_num:
            matching_entries.append((idx, e))
    
    if not matching_entries:
        return jsonify({'error': 'no matching regular grades found'}), 404
    
    if grade_index is not None:
        if grade_index >= len(matching_entries):
            return jsonify({'error': 'grade index out of range'}), 400
        idx_to_edit = matching_entries[grade_index][0]
    else:
        idx_to_edit = matching_entries[-1][0]

    entries[idx_to_edit]['grade'] = new_grade_val
    write_store(entries)
    sem1 = compute_semester_avg(entries, 1)
    sem2 = compute_semester_avg(entries, 2)
    avg = compute_avg(entries)
    return jsonify({
        'success': True,
        'entries': entries,
        'average': round(avg, 2) if avg is not None else None,
        'semesterAverages': {
            '1': round(sem1, 2) if sem1 is not None else None,
            '2': round(sem2, 2) if sem2 is not None else None,
        }
    })


if __name__ == '__main__':
    app.run(debug=True)