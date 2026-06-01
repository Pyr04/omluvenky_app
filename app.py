from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///omluvenky.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db = SQLAlchemy(app)

# 1. NOVÁ TABULKA: Hodnosti
class Hodnost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(50), nullable=False)

# 2. UPRAVENÁ TABULKA: Člen
class Clen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(50), nullable=False)
    # Cizí klíč ukazující na ID hodnosti
    hodnost_id = db.Column(db.Integer, db.ForeignKey('hodnost.id'), nullable=False)
    # Vztah, abychom v HTML mohli napsat clen.hodnost.nazev
    hodnost = db.relationship('Hodnost')

class Omluvenka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datum_od = db.Column(db.String(20), nullable=False)
    datum_do = db.Column(db.String(20), nullable=False)
    clen_id = db.Column(db.Integer, db.ForeignKey('clen.id'), nullable=False)

    clen = db.relationship('Clen', backref='vsechny_omluvenky')

with app.app_context():
    db.create_all()
    # 3. CHYTRÝ TRIK: Pokud v databázi nejsou žádné hodnosti, vytvoříme výchozí
    if not Hodnost.query.first():
        db.session.add_all([
            Hodnost(nazev="WOC"),
            Hodnost(nazev="WO1"),
            Hodnost(nazev="CW2"),
            Hodnost(nazev="CW3"),
            Hodnost(nazev="CW4"),
            Hodnost(nazev="CW5"),
            Hodnost(nazev="2.LT"),
            Hodnost(nazev="1.LT"),
            Hodnost(nazev="CPT"),
        ])
        db.session.commit()

@app.route('/')
def index():
    clenove_z_db = Clen.query.all()
    # Musíme do HTML poslat i seznam všech hodností pro náš formulář
    hodnosti_z_db = Hodnost.query.all()
    return render_template('index.html', clenove=clenove_z_db, hodnosti=hodnosti_z_db)

@app.route('/pridat', methods=['POST'])
def pridat_clena():
    jmeno_z_formulare = request.form['jmeno']
    hodnost_id_z_formulare = request.form['hodnost'] # Nyní posíláme ID hodnosti, ne název
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
    od = request.form['datum_od']
    do = request.form['datum_do']
    nova_omluvenka = Omluvenka(datum_od=od, datum_do=do, clen_id=clen_id)
    db.session.add(nova_omluvenka)
    db.session.commit()
    return redirect(url_for('profil', id=clen_id))

@app.route('/zmenit_hodnost/<int:clen_id>', methods=['POST'])
def zmenit_hodnost(clen_id):
    clen = Clen.query.get_or_404(clen_id)
    clen.hodnost_id = request.form['hodnost'] # Měníme ID hodnosti
    db.session.commit()
    return redirect(url_for('profil', id=clen_id))


@app.route('/smazat_clena/<int:clen_id>', methods=['POST'])
def smazat_clena(clen_id):
    clen = Clen.query.get_or_404(clen_id)
    
    # BEZPEČNOST: Nejdříve smažeme všechny omluvenky, které patří k tomuto členovi
    Omluvenka.query.filter_by(clen_id=clen_id).delete()
    
    # Poté smažeme samotného člena
    db.session.delete(clen)
    db.session.commit()
    
    return redirect(url_for('index'))


@app.route('/omluvenky', methods=['GET', 'POST'])
def omluvenky_stranka():
    if request.method == 'POST':
        # Získání dat z centrálního formuláře
        clen_id = request.form.get('clen_id')
        datum_od_str = request.form.get('datum_od')
        datum_do_str = request.form.get('datum_do')
        
        # Převod textu na datum (pokud už máš datetime importovaný nahoře, bude to fungovat)
        from datetime import datetime
        datum_od = datetime.strptime(datum_od_str, '%Y-%m-%d').date()
        datum_do = datetime.strptime(datum_do_str, '%Y-%m-%d').date()
        
        # Uložení do databáze
        nova_omluvenka = Omluvenka(datum_od=datum_od, datum_do=datum_do, clen_id=clen_id)
        db.session.add(nova_omluvenka)
        db.session.commit()
        
        return redirect(url_for('omluvenky_stranka'))
        
    # Pokud se stránka jen načítá (GET)
    vsechni_clenove = Clen.query.all()
    # Seřadíme omluvenky od nejnovějších
    vsechny_omluvenky = Omluvenka.query.order_by(Omluvenka.datum_od.desc()).all()
    
    return render_template('omluvenky.html', clenove=vsechni_clenove, omluvenky=vsechny_omluvenky)

if __name__ == '__main__':
    app.run(debug=True)