from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///omluvenky.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db = SQLAlchemy(app)

# 1. TABULKA: Hodnosti
class Hodnost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(50), nullable=False)

# 2. TABULKA: Člen
class Clen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(50), nullable=False)
    hodnost_id = db.Column(db.Integer, db.ForeignKey('hodnost.id'), nullable=False)
    hodnost = db.relationship('Hodnost')

# 3. TABULKA: Omluvenka
class Omluvenka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datum_od = db.Column(db.Date, nullable=False) 
    datum_do = db.Column(db.Date, nullable=False) 
    clen_id = db.Column(db.Integer, db.ForeignKey('clen.id'), nullable=False)
    clen = db.relationship('Clen', backref='vsechny_omluvenky')

# 4. TABULKA: Typ Akce
class TypAkce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(50), nullable=False)
    vsechny_akce = db.relationship('Akce', backref='typ_akce')
 
# 5. TABULKA: Akce
class Akce(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(100), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    typ_id = db.Column(db.Integer, db.ForeignKey('typ_akce.id'), nullable=False)
    probehla = db.Column(db.Boolean, default=False)

# 6. TABULKA: Účast na akci
class Ucast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    akce_id = db.Column(db.Integer, db.ForeignKey('akce.id'), nullable=False)
    clen_id = db.Column(db.Integer, db.ForeignKey('clen.id'), nullable=False)
    stav = db.Column(db.String(20), nullable=False, default='Nezadáno')
    akce = db.relationship('Akce', backref=db.backref('ucasti', cascade="all, delete-orphan"))
    clen = db.relationship('Clen', backref='ucasti')

# Vytvoření databáze a výchozích hodnot
with app.app_context():
    db.create_all()
    if not Hodnost.query.first():
        db.session.add_all([
            Hodnost(nazev="WOC"), Hodnost(nazev="WO1"), Hodnost(nazev="CW2"),
            Hodnost(nazev="CW3"), Hodnost(nazev="CW4"), Hodnost(nazev="CW5"),
            Hodnost(nazev="2.LT"), Hodnost(nazev="1.LT"), Hodnost(nazev="CPT"),
        ])
        db.session.commit()

# ==========================================
# SPRÁVA ČLENŮ A OMLUVENEK (Hlavní stránka)
# ==========================================
@app.route('/')
def index():
    clenove_z_db = Clen.query.all()
    hodnosti_z_db = Hodnost.query.all()
    return render_template('index.html', clenove=clenove_z_db, hodnosti=hodnosti_z_db)

@app.route('/pridat', methods=['POST'])
def pridat_clena():
    jmeno_z_formulare = request.form['jmeno']
    hodnost_id_z_formulare = request.form['hodnost']
    novy_clen = Clen(jmeno=jmeno_z_formulare, hodnost_id=hodnost_id_z_formulare)
    db.session.add(novy_clen)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/profil/<int:id>')
def profil(id):
    vybrany_clen = Clen.query.get_or_404(id)
    omluvenky_clena = Omluvenka.query.filter_by(clen_id=id).all()
    hodnosti_z_db = Hodnost.query.all()
    return render_template('profil.html', clen=vybrany_clen, omluvenky=omluvenky_clena, hodnosti=hodnosti_z_db)

@app.route('/pridat_omluvenku/<int:clen_id>', methods=['POST'])
def pridat_omluvenku(clen_id):
    od_str = request.form['datum_od']
    do_str = request.form['datum_do']
    od = datetime.strptime(od_str, '%Y-%m-%d').date()
    do = datetime.strptime(do_str, '%Y-%m-%d').date()
    nova_omluvenka = Omluvenka(datum_od=od, datum_do=do, clen_id=clen_id)
    db.session.add(nova_omluvenka)
    db.session.commit()
    return redirect(url_for('profil', id=clen_id))

@app.route('/zmenit_hodnost/<int:clen_id>', methods=['POST'])
def zmenit_hodnost(clen_id):
    clen = Clen.query.get_or_404(clen_id)
    clen.hodnost_id = request.form['hodnost']
    db.session.commit()
    return redirect(url_for('profil', id=clen_id))

@app.route('/smazat_clena/<int:clen_id>', methods=['POST'])
def smazat_clena(clen_id):
    clen = Clen.query.get_or_404(clen_id)
    
    
    Omluvenka.query.filter_by(clen_id=clen_id).delete()
    
    
    Ucast.query.filter_by(clen_id=clen_id).delete()
    
    
    db.session.delete(clen)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/omluvenky', methods=['GET', 'POST'])
def omluvenky_stranka():
    if request.method == 'POST':
        clen_id = request.form.get('clen_id')
        datum_od_str = request.form.get('datum_od')
        datum_do_str = request.form.get('datum_do')
        datum_od = datetime.strptime(datum_od_str, '%Y-%m-%d').date()
        datum_do = datetime.strptime(datum_do_str, '%Y-%m-%d').date()
        nova_omluvenka = Omluvenka(datum_od=datum_od, datum_do=datum_do, clen_id=clen_id)
        db.session.add(nova_omluvenka)
        db.session.commit()
        return redirect(url_for('omluvenky_stranka'))
    
    
        
    vsechni_clenove = Clen.query.all()
    vsechny_omluvenky = Omluvenka.query.order_by(Omluvenka.datum_od.desc()).all()
    return render_template('omluvenky.html', clenove=vsechni_clenove, omluvenky=vsechny_omluvenky)


@app.route('/smazat_omluvenku/<int:omluvenka_id>', methods=['POST'])
def smazat_omluvenku(omluvenka_id):
    # Najde omluvenku podle ID
    omluvenka = Omluvenka.query.get_or_404(omluvenka_id)
    
    # Smaže ji z databáze
    db.session.delete(omluvenka)
    db.session.commit()
    
    # Chytré přesměrování: vrátí tě zpět na stránku, ze které jsi tlačítko kliknul 
    # (ať už jsi byl v celkovém seznamu omluvenek, nebo na profilu konkrétního člena)
    return redirect(request.referrer or url_for('omluvenky_stranka'))
# ==========================================
# DASHBOARD (Přesunut na tlačítko v menu)
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

    hodnosti_data = db.session.query(Hodnost.nazev, db.func.count(Clen.id)).join(Clen).group_by(Hodnost.id).all()
    hodnosti_labels = [row[0] for row in hodnosti_data]
    hodnosti_counts = [row[1] for row in hodnosti_data]
    
    probehle_akce = Akce.query.filter_by(probehla=True).order_by(Akce.datum.asc()).limit(10).all()
    akce_labels = [akce.nazev for akce in probehle_akce]
    akce_ucast_counts = []
    
    for akce in probehle_akce:
        # Počítáme jen ty, co byli fyzicky přítomni (Přítomen nebo Pozdní příchod)
        ucast_count = Ucast.query.filter(
            Ucast.akce_id == akce.id,
            Ucast.stav.in_(['Přítomen', 'Pozdní příchod'])
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
# AKCE A STRIKE SYSTÉM
# ==========================================
@app.route('/akce', methods=['GET', 'POST'])
def akce_stranka():
    if request.method == 'POST':
        nazev = request.form.get('nazev')
        datum_str = request.form.get('datum')
        typ_id = request.form.get('typ_id')
        datum = datetime.strptime(datum_str, '%Y-%m-%d').date()
        nova_akce = Akce(nazev=nazev, datum=datum, typ_id=typ_id)
        db.session.add(nova_akce)
        db.session.commit()
        return redirect(url_for('akce_stranka'))
        
    typy_akci = TypAkce.query.all()
    if not typy_akci:
        db.session.add(TypAkce(nazev='Mise (povinná)'))
        db.session.add(TypAkce(nazev='Trénink'))
        db.session.add(TypAkce(nazev='Mise (nepovinná)'))
        db.session.commit()
        typy_akci = TypAkce.query.all()

    vsechny_akce = Akce.query.order_by(Akce.datum.asc()).all()
    return render_template('akce.html', typy_akci=typy_akci, akce_seznam=vsechny_akce, dnesni_datum=date.today())

@app.route('/akce/<int:akce_id>', methods=['GET', 'POST'])
def detail_akce(akce_id):
    akce = Akce.query.get_or_404(akce_id)
    vsechni_clenove = Clen.query.all()
    
    for clen in vsechni_clenove:
        ucast = Ucast.query.filter_by(akce_id=akce.id, clen_id=clen.id).first()
        ma_omluvenku = Omluvenka.query.filter(
            Omluvenka.clen_id == clen.id,
            Omluvenka.datum_od <= akce.datum,
            Omluvenka.datum_do >= akce.datum
        ).first()
        
        if not ucast:
            novy_stav = 'Omluven' if ma_omluvenku else 'Nezadáno'
            ucast = Ucast(akce_id=akce.id, clen_id=clen.id, stav=novy_stav)
            db.session.add(ucast)
        else:
            if not akce.probehla:
                if ma_omluvenku and ucast.stav == 'Nezadáno':
                    ucast.stav = 'Omluven'
                elif not ma_omluvenku and ucast.stav == 'Omluven':
                    ucast.stav = 'Nezadáno'
            
    db.session.commit()
    
    if request.method == 'POST':
        for clen in vsechni_clenove:
            odeslany_stav = request.form.get(f'stav_{clen.id}')
            if odeslany_stav and odeslany_stav != 'Omluven_disabled':
                ucast = Ucast.query.filter_by(akce_id=akce.id, clen_id=clen.id).first()
                ucast.stav = odeslany_stav
                
        akce.probehla = True
        db.session.commit()
        return redirect(url_for('detail_akce', akce_id=akce.id))
        
    ucasti = Ucast.query.filter_by(akce_id=akce.id).all()
    ucast_dict = {u.clen_id: u.stav for u in ucasti}
    
    return render_template('detail_akce.html', akce=akce, clenove=vsechni_clenove, ucast_dict=ucast_dict)

@app.route('/smazat_akci/<int:akce_id>', methods=['POST'])
def smazat_akci(akce_id):
    akce = Akce.query.get_or_404(akce_id)
    Ucast.query.filter_by(akce_id=akce_id).delete()
    db.session.delete(akce)
    db.session.commit()
    return redirect(url_for('akce_stranka'))

@app.route('/strike')
def strike_stranka():
    probehle_akce = Akce.query.filter_by(probehla=True).order_by(Akce.datum.desc()).all()
    return render_template('strike.html', akce_seznam=probehle_akce)

@app.route('/strike/<int:akce_id>')
def detail_strike(akce_id):
    akce = Akce.query.get_or_404(akce_id)
    hrisnici = Ucast.query.filter(
        Ucast.akce_id == akce.id,
        Ucast.stav.in_(['AWOL', 'Pozdní příchod'])
    ).all()
    return render_template('detail_strike.html', akce=akce, hrisnici=hrisnici)

if __name__ == '__main__':
    app.run(debug=True)