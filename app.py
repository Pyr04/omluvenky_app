from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

# ==========================================
# 1. KONFIGURACE APLIKACE A DATABÁZE
# ==========================================
app = Flask(__name__)
app.secret_key = 'super_tajny_klic_letky_160'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///omluvenky.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Tvé velitelské heslo (nyní Spartans160)
VELITEL_HESLO_HASH = generate_password_hash("Spartans160")

# ==========================================
# 2. BEZPEČNOSTNÍ ZÁMEK (DEKORÁTOR)
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('prihlasen'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 3. DATABÁZOVÉ MODELY
# ==========================================
class Hodnost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(50), nullable=False)
    clenove = db.relationship('Clen', backref='hodnost', lazy=True)

class Clen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(100), nullable=False)
    hodnost_id = db.Column(db.Integer, db.ForeignKey('hodnost.id'), nullable=False)
    omluvenky = db.relationship('Omluvenka', backref='clen', lazy=True, cascade="all, delete-orphan")
    ucasti = db.relationship('Ucast', backref='clen', lazy=True, cascade="all, delete-orphan")

class Akce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(100), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    probehla = db.Column(db.Boolean, default=False)
    ucasti = db.relationship('Ucast', backref='akce', lazy=True, cascade="all, delete-orphan")

class Omluvenka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clen_id = db.Column(db.Integer, db.ForeignKey('clen.id'), nullable=False)
    datum_od = db.Column(db.Date, nullable=False)
    datum_do = db.Column(db.Date, nullable=False)

class Ucast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clen_id = db.Column(db.Integer, db.ForeignKey('clen.id'), nullable=False)
    akce_id = db.Column(db.Integer, db.ForeignKey('akce.id'), nullable=False)
    stav = db.Column(db.String(50), default='Nezadáno')

# ==========================================
# 4. SYSTÉM PŘIHLÁŠENÍ (STRÁŽNICE)
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    chyba = None
    if request.method == 'POST':
        zadane_heslo = request.form.get('heslo')
        if check_password_hash(VELITEL_HESLO_HASH, zadane_heslo):
            session['prihlasen'] = True
            return redirect(url_for('dashboard'))
        else:
            chyba = "Přístup odepřen: Nesprávné velitelské heslo."
    return render_template('login.html', chyba=chyba)

@app.route('/logout')
def logout():
    session.pop('prihlasen', None)
    return redirect(url_for('dashboard'))

# ==========================================
# 5. VEŘEJNÝ DASHBOARD (BEZ ZÁMKU)
# ==========================================
@app.route('/dashboard')
def dashboard():
    pocet_clenu = Clen.query.count()
    pocet_akci = Akce.query.filter_by(probehla=True).count()
    
    dnes = date.today()
    aktivni_omluvenky = Omluvenka.query.filter(
        Omluvenka.datum_od <= dnes, 
        Omluvenka.datum_do >= dnes
    ).count()
    
    pocet_strike = Ucast.query.filter(Ucast.stav.in_(['AWOL', 'Pozdní příchod'])).count()

    # Data pro grafy
    hodnosti_data = db.session.query(Hodnost.nazev, db.func.count(Clen.id)).join(Clen).group_by(Hodnost.id).all()
    hodnosti_labels = [row[0] for row in hodnosti_data]
    hodnosti_counts = [row[1] for row in hodnosti_data]
    
    probehle_akce = Akce.query.filter_by(probehla=True).order_by(Akce.datum.asc()).limit(10).all()
    akce_labels = [akce.nazev for akce in probehle_akce]
    akce_ucast_counts = []
    
    for akce in probehle_akce:
        ucast_count = Ucast.query.filter(
            Ucast.akce_id == akce.id,
            ~Ucast.stav.in_(['AWOL', 'Omluven', 'Nezadáno'])
        ).count()
        akce_ucast_counts.append(ucast_count)

    hrisnici_data = db.session.query(Clen.jmeno, db.func.count(Ucast.id)).join(Ucast).filter(
        Ucast.stav.in_(['AWOL', 'Pozdní příchod'])
    ).group_by(Clen.id).order_by(db.func.count(Ucast.id).desc()).limit(5).all()
    
    hrisnici_labels = [row[0] for row in hrisnici_data]
    hrisnici_counts = [row[1] for row in hrisnici_data]

    return render_template('dashboard.html', 
                           clenu=pocet_clenu, akci=pocet_akci, omluvenek=aktivni_omluvenky, striku=pocet_strike,
                           hodnosti_labels=hodnosti_labels, hodnosti_counts=hodnosti_counts,
                           akce_labels=akce_labels, akce_ucast_counts=akce_ucast_counts,
                           hrisnici_labels=hrisnici_labels, hrisnici_counts=hrisnici_counts)

# ==========================================
# 6. ZAMČENÉ TRASY (ADMINISTRACE DATABÁZE)
# ==========================================
@app.route('/')
@login_required
def index():
    clenove = Clen.query.all()
    hodnosti = Hodnost.query.all()
    return render_template('index.html', clenove=clenove, hodnosti=hodnosti)

@app.route('/omluvenky', methods=['GET', 'POST'])
@login_required
def omluvenky_stranka():
    if request.method == 'POST':
        clen_id = request.form.get('clen_id')
        datum_od_str = request.form.get('datum_od')
        datum_do_str = request.form.get('datum_do')
        
        if clen_id and datum_od_str and datum_do_str:
            datum_od = datetime.strptime(datum_od_str, '%Y-%m-%d').date()
            datum_do = datetime.strptime(datum_do_str, '%Y-%m-%d').date()
            nova_omluvenka = Omluvenka(clen_id=clen_id, datum_od=datum_od, datum_do=datum_do)
            db.session.add(nova_omluvenka)
            db.session.commit()
            return redirect(url_for('omluvenky_stranka'))

    omluvenky = Omluvenka.query.order_by(Omluvenka.datum_od.desc()).all()
    clenove = Clen.query.all()
    return render_template('omluvenky.html', omluvenky=omluvenky, clenove=clenove)

@app.route('/akce', methods=['GET', 'POST'])
@login_required
def akce_stranka():
    # Zde máš zřejmě logiku pro přidávání a výpis akcí
    akce_vsechny = Akce.query.order_by(Akce.datum.desc()).all()
    return render_template('akce.html', akce=akce_vsechny)

@app.route('/strike')
@login_required
def strike_stranka():
    # Zde máš zřejmě logiku pro výpis STRIKE prohřešků
    return render_template('strike.html')

# ==========================================
# 7. SPUŠTĚNÍ APLIKACE A VYTVOŘENÍ DATABÁZE
# ==========================================
if __name__ == '__main__':
    with app.app_context():
        # Vytvoří tabulky, pokud ještě neexistují
        db.create_all()
        
        

    app.run(debug=True)