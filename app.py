from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lo_khai_construction_secret_key')

# Lấy URL kết nối PostgreSQL từ biến môi trường của Render
DB_URL = os.environ.get('DATABASE_URL')


def get_db():
    # Sử dụng RealDictCursor để kết quả trả về có dạng dict giống như sqlite3.Row
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    if not DB_URL:
        print("Cảnh báo: Chưa cấu hình biến môi trường DATABASE_URL!")
        return
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Bảng Công ty
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company (
                ma_cty VARCHAR(50) PRIMARY KEY,
                ten_cty VARCHAR(255) NOT NULL,
                dia_chi TEXT,
                so_dien_thoai VARCHAR(20),
                nguoi_dai_dien VARCHAR(100)
            );
        ''')

        # Bảng Phòng ban
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS department (
                ma_pb VARCHAR(50) PRIMARY KEY,
                ten_pb VARCHAR(255) NOT NULL,
                ma_cty VARCHAR(50) REFERENCES company(ma_cty) ON DELETE CASCADE,
                truong_phong VARCHAR(100),
                so_nhan_su INTEGER
            );
        ''')

        # Bảng Công trình
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project (
                ma_ct VARCHAR(50) PRIMARY KEY,
                ten_ct VARCHAR(255) NOT NULL,
                dia_diem TEXT,
                chu_dau_tu VARCHAR(255),
                trang_thai VARCHAR(100),
                ma_cty VARCHAR(50)
            );
        ''')

        # Giữ cột ma_cty cũ để tương thích, nhưng bỏ FK cũ để xóa một công ty
        # không xóa cả công trình đang được nhiều công ty cùng liên kết.
        cursor.execute('ALTER TABLE project DROP CONSTRAINT IF EXISTS project_ma_cty_fkey;')

        # Bảng trung gian: một công ty có thể tham gia nhiều công trình
        # và một công trình có thể liên kết với nhiều công ty.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_project (
                ma_cty VARCHAR(50) NOT NULL
                    REFERENCES company(ma_cty) ON DELETE CASCADE,
                ma_ct VARCHAR(50) NOT NULL
                    REFERENCES project(ma_ct) ON DELETE CASCADE,
                vai_tro VARCHAR(100),
                PRIMARY KEY (ma_cty, ma_ct)
            );
        ''')

        # Chuyển liên kết cũ từ project.ma_cty sang bảng trung gian.
        # Có thể chạy lặp lại an toàn khi ứng dụng khởi động.
        cursor.execute('''
            INSERT INTO company_project (ma_cty, ma_ct)
            SELECT ma_cty, ma_ct
            FROM project
            WHERE ma_cty IS NOT NULL
            ON CONFLICT (ma_cty, ma_ct) DO NOTHING;
        ''')

        # Bảng Hạng mục
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS item (
                ma_hm VARCHAR(50) PRIMARY KEY,
                ten_hm VARCHAR(255) NOT NULL,
                ma_ct VARCHAR(50) REFERENCES project(ma_ct) ON DELETE CASCADE,
                kinh_phi NUMERIC(15, 2),
                tien_do VARCHAR(100)
            );
        ''')

        conn.commit()
        cursor.close()
        conn.close()
        print("Khởi tạo PostgreSQL Database thành công!")
    except Exception as e:
        print("Lỗi khởi tạo Database:", e)


init_db()


# --- ROUTES AUTHENTICATION ---
@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/set-session', methods=['POST'])
def set_session():
    data = request.json or {}
    email = data.get('email')
    if email:
        session['user'] = email
        return jsonify({'success': True})
    return jsonify({'success': False}), 400


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_fullname = session.get('user', 'Tài khoản')
    return render_template('index.html', user_fullname=user_fullname)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- API CÔNG TY ---
@app.route('/api/company', methods=['GET', 'POST'])
def api_company():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute('''
            INSERT INTO company (ma_cty, ten_cty, dia_chi, so_dien_thoai, nguoi_dai_dien)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ma_cty) DO UPDATE SET
                ten_cty = EXCLUDED.ten_cty,
                dia_chi = EXCLUDED.dia_chi,
                so_dien_thoai = EXCLUDED.so_dien_thoai,
                nguoi_dai_dien = EXCLUDED.nguoi_dai_dien;
        ''', (data.get('ma_cty'), data.get('ten_cty'), data.get('dia_chi'), data.get('so_dien_thoai'),
              data.get('nguoi_dai_dien')))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    else:
        cursor.execute('SELECT * FROM company;')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)


@app.route('/api/company/<ma_cty>', methods=['DELETE'])
def del_company(ma_cty):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM company WHERE ma_cty = %s;', (ma_cty,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})


# --- API PHÒNG BAN ---
@app.route('/api/department', methods=['GET', 'POST'])
def api_department():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute('''
            INSERT INTO department (ma_pb, ten_pb, ma_cty, truong_phong, so_nhan_su)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ma_pb) DO UPDATE SET
                ten_pb = EXCLUDED.ten_pb,
                ma_cty = EXCLUDED.ma_cty,
                truong_phong = EXCLUDED.truong_phong,
                so_nhan_su = EXCLUDED.so_nhan_su;
        ''', (data.get('ma_pb'), data.get('ten_pb'), data.get('ma_cty'), data.get('truong_phong'),
              data.get('so_nhan_su')))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    else:
        cursor.execute('SELECT * FROM department;')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)


@app.route('/api/department/<ma_pb>', methods=['DELETE'])
def del_department(ma_pb):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM department WHERE ma_pb = %s;', (ma_pb,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})


# --- API CÔNG TRÌNH ---
@app.route('/api/project', methods=['GET', 'POST'])
def api_project():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json or {}
        # Hỗ trợ cả giao diện mới (danh sách) và dữ liệu cũ (một ma_cty).
        company_ids = data.get('ma_cty_list')
        if company_ids is None:
            legacy_company_id = data.get('ma_cty')
            company_ids = [legacy_company_id] if legacy_company_id else []
        company_ids = list(dict.fromkeys(cid for cid in company_ids if cid))

        # Giữ ma_cty cũ với công ty đầu tiên để tương thích dữ liệu/API cũ.
        legacy_company_id = company_ids[0] if company_ids else data.get('ma_cty')
        cursor.execute('''
            INSERT INTO project (ma_ct, ten_ct, dia_diem, chu_dau_tu, trang_thai, ma_cty)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (ma_ct) DO UPDATE SET
                ten_ct = EXCLUDED.ten_ct,
                dia_diem = EXCLUDED.dia_diem,
                chu_dau_tu = EXCLUDED.chu_dau_tu,
                trang_thai = EXCLUDED.trang_thai,
                ma_cty = EXCLUDED.ma_cty;
        ''', (data.get('ma_ct'), data.get('ten_ct'), data.get('dia_diem'), data.get('chu_dau_tu'),
              data.get('trang_thai'), legacy_company_id))

        # Cập nhật các liên kết n–m cho công trình.
        cursor.execute('DELETE FROM company_project WHERE ma_ct = %s;', (data.get('ma_ct'),))
        for company_id in company_ids:
            cursor.execute('''
                INSERT INTO company_project (ma_cty, ma_ct)
                VALUES (%s, %s)
                ON CONFLICT (ma_cty, ma_ct) DO NOTHING;
            ''', (company_id, data.get('ma_ct')))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    else:
        cursor.execute('''
            SELECT p.*,
                   COALESCE(
                       ARRAY_AGG(cp.ma_cty) FILTER (WHERE cp.ma_cty IS NOT NULL),
                       ARRAY[]::VARCHAR[]
                   ) AS ma_cty_list
            FROM project p
            LEFT JOIN company_project cp ON cp.ma_ct = p.ma_ct
            GROUP BY p.ma_ct
            ORDER BY p.ma_ct;
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)


@app.route('/api/project/<ma_ct>', methods=['DELETE'])
def del_project(ma_ct):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM project WHERE ma_ct = %s;', (ma_ct,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})


# --- API HẠNG MỤC ---
@app.route('/api/item', methods=['GET', 'POST'])
def api_item():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute('''
            INSERT INTO item (ma_hm, ten_hm, ma_ct, kinh_phi, tien_do)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ma_hm) DO UPDATE SET
                ten_hm = EXCLUDED.ten_hm,
                ma_ct = EXCLUDED.ma_ct,
                kinh_phi = EXCLUDED.kinh_phi,
                tien_do = EXCLUDED.tien_do;
        ''', (data.get('ma_hm'), data.get('ten_hm'), data.get('ma_ct'), data.get('kinh_phi'), data.get('tien_do')))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    else:
        cursor.execute('SELECT * FROM item;')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows)


@app.route('/api/item/<ma_hm>', methods=['DELETE'])
def del_item(ma_hm):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM item WHERE ma_hm = %s;', (ma_hm,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})


# --- API TRA CỨU ---
@app.route('/api/search', methods=['GET'])
def api_search():
    ma_cty = request.args.get('ma_cty')
    if not ma_cty:
        return jsonify({'success': False, 'message': 'Thiếu tham số ma_cty'})

    conn = get_db()
    cursor = conn.cursor()

    query = '''
        SELECT p.ten_ct,
               i.ten_hm,
               i.kinh_phi,
               i.tien_do
        FROM item i
        JOIN project p ON i.ma_ct = p.ma_ct
        JOIN company_project cp ON cp.ma_ct = p.ma_ct
        WHERE cp.ma_cty = %s;
    '''
    cursor.execute(query, (ma_cty,))
    rows = cursor.fetchall()

    total_money = sum(float(r['kinh_phi']) for r in rows if r['kinh_phi'] is not None)

    cursor.close()
    conn.close()

    return jsonify({
        'success': True,
        'data': rows,
        'total_money': total_money
    })


if __name__ == '__main__':
    app.run(debug=True)
