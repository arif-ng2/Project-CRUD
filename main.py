import pymysql
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional

from sqlalchemy import create_engine, Column, Integer, String, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ==========================================
# 0. KONFIGURASI DATABASE
# ==========================================
koneksi_awal = pymysql.connect(host='localhost', user='root', password='')
cursor = koneksi_awal.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS toko_hp")
koneksi_awal.close()

DATABASE_URL = "mysql+pymysql://root:@localhost:3306/toko_hp"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==========================================
# 1. MODEL DATABASE
# ==========================================
class HandphoneDB(Base):
    __tablename__ = "handphone"
    
    id = Column(Integer, primary_key=True, index=True)
    merk = Column(String(50))
    model = Column(String(100))
    harga = Column(Integer)
    stok = Column(Integer)
    warna = Column(String(50))

Base.metadata.create_all(bind=engine)

# ==========================================
# 2. SCHEMA PYDANTIC
# ==========================================
class HPCreate(BaseModel):
    merk: str
    model: str
    harga: int
    stok: int
    warna: str

class HPResponse(HPCreate):
    id: int
    class Config:
        from_attributes = True

app = FastAPI(title="Sistem Stok HP")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. FRONTEND (HTML & JS)
# ==========================================
@app.get("/", response_class=HTMLResponse)
def halaman_web():
    return """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>Manajemen Stok HP</title>
        <style>
            body { font-family: sans-serif; max-width: 900px; margin: 20px auto; padding: 20px; background: #f4f4f4; }
            .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            
            /* TAMPILAN FORM BARU (GRID 2 KOLOM) */
            .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
            .form-group { display: flex; flex-direction: column; }
            .form-group label { margin-bottom: 5px; font-weight: bold; font-size: 14px; color: #333; }
            .form-group input { padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; outline: none; }
            .form-group input:focus { border-color: #4f46e5; }
            .form-full { grid-column: span 2; }
            .button-group { display: flex; gap: 10px; justify-content: flex-end; }
            
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f8fafc; }
            
            .btn { padding: 10px 16px; cursor: pointer; border: none; border-radius: 4px; font-weight: bold; }
            .btn-save { background: #4f46e5; color: white; }
            .btn-save:hover { background: #4338ca; }
            .btn-edit { background: #f59e0b; color: white; padding: 6px 10px; }
            .btn-del { background: #ef4444; color: white; padding: 6px 10px; }
            .btn-reset { background: #6b7280; color: white; }
            
            .search-box { padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; outline: none; }
            .search-box:focus { border-color: #4f46e5; }
            .search-container { display: flex; gap: 10px; align-items: center; }
        </style>
    </head>
    <body>
        <h1>📱 Stok Handphone</h1>
        
        <!-- FORM TAMBAH/EDIT HP (DIPERBARUI) -->
        <div class="card">
            <h2 id="formTitle" style="margin-top: 0; margin-bottom: 20px; color: #1f2937;">Tambah HP Baru</h2>
            <form id="formHP">
                <div class="form-grid">
                    <div class="form-group">
                        <label for="merk">Merk HP</label>
                        <input type="text" id="merk" placeholder="Contoh: Samsung" required>
                    </div>
                    <div class="form-group">
                        <label for="model">Model / Tipe</label>
                        <input type="text" id="model" placeholder="Contoh: Galaxy S24" required>
                    </div>
                    <div class="form-group">
                        <label for="harga">Harga Jual (Rp)</label>
                        <input type="number" id="harga" placeholder="Contoh: 15000000" min="0" required>
                    </div>
                    <div class="form-group">
                        <label for="stok">Jumlah Stok Tersedia</label>
                        <input type="number" id="stok" placeholder="Contoh: 10" min="0" required>
                    </div>
                    <div class="form-group form-full">
                        <label for="warna">Warna Pilihan</label>
                        <input type="text" id="warna" placeholder="Contoh: Hitam, Titanium" required>
                    </div>
                </div>
                <div class="button-group">
                    <button type="button" id="btnBatal" class="btn btn-reset" style="display:none;" onclick="batal()">Batal Edit</button>
                    <button type="submit" id="btnSubmit" class="btn btn-save">💾 Simpan Data</button>
                </div>
            </form>
        </div>

        <!-- FITUR PENCARIAN (Tetap di bawah form) -->
        <div class="card search-container">
            <input type="text" id="inputCari" class="search-box" style="flex: 1; margin: 0;" placeholder="🔍 Cari Merk atau Model HP (Contoh: Samsung)...">
            <button onclick="cariData()" class="btn btn-save" style="padding: 12px 20px;">Cari</button>
            <button onclick="resetCari()" class="btn btn-reset" style="padding: 12px 20px;">Reset</button>
        </div>
        
        <!-- TABEL DATA -->
        <table>
            <thead>
                <tr>
                    <th>Merk</th><th>Model</th><th>Harga</th><th>Stok</th><th>Warna</th><th>Aksi</th>
                </tr>
            </thead>
            <tbody id="tabelHP"></tbody>
        </table>

        <script>
            let editId = null;
            
            async function muatData(query = "") {
                const url = query ? `/hp/?q=${encodeURIComponent(query)}` : '/hp/';
                const res = await fetch(url);
                const data = await res.json();
                const tbody = document.getElementById('tabelHP');
                
                if (data.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: red; padding: 20px;">Data tidak ditemukan</td></tr>`;
                    return;
                }

                tbody.innerHTML = data.map(hp => `
                    <tr>
                        <td>${hp.merk}</td><td>${hp.model}</td><td>Rp ${hp.harga.toLocaleString('id-ID')}</td>
                        <td><strong>${hp.stok}</strong></td><td>${hp.warna}</td>
                        <td>
                            <button class="btn btn-edit" onclick="edit(${hp.id}, '${hp.merk}', '${hp.model}', ${hp.harga}, ${hp.stok}, '${hp.warna}')">✏️ Edit</button>
                            <button class="btn btn-del" onclick="hapus(${hp.id})">🗑️ Hapus</button>
                        </td>
                    </tr>`).join('');
            }

            function cariData() {
                const kataKunci = document.getElementById('inputCari').value;
                muatData(kataKunci);
            }

            function resetCari() {
                document.getElementById('inputCari').value = "";
                muatData(""); 
            }

            document.getElementById('formHP').onsubmit = async (e) => {
                e.preventDefault();
                const data = {
                    merk: document.getElementById('merk').value,
                    model: document.getElementById('model').value,
                    harga: parseInt(document.getElementById('harga').value),
                    stok: parseInt(document.getElementById('stok').value),
                    warna: document.getElementById('warna').value
                };
                const url = editId ? `/hp/${editId}` : '/hp/';
                await fetch(url, { method: editId ? 'PUT' : 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                
                batal(); 
                muatData(document.getElementById('inputCari').value);
            };

            function edit(id, merk, model, harga, stok, warna) {
                editId = id; 
                document.getElementById('merk').value = merk;
                document.getElementById('model').value = model;
                document.getElementById('harga').value = harga;
                document.getElementById('stok').value = stok;
                document.getElementById('warna').value = warna;
                document.getElementById('formTitle').innerText = "Edit Data HP";
                document.getElementById('btnSubmit').innerText = "💾 Update Data";
                document.getElementById('btnBatal').style.display = "inline-block";
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function batal() { 
                editId = null; 
                document.getElementById('formHP').reset(); 
                document.getElementById('formTitle').innerText = "Tambah HP Baru";
                document.getElementById('btnSubmit').innerText = "💾 Simpan Data";
                document.getElementById('btnBatal').style.display = "none"; 
            }
            
            async function hapus(id) { 
                if(confirm("Yakin ingin menghapus data ini?")) {
                    await fetch(`/hp/${id}`, { method: 'DELETE' }); 
                    muatData(document.getElementById('inputCari').value); 
                }
            }
            
            // Tambahan: Tekan "Enter" di kotak pencarian akan langsung mencari
            document.getElementById("inputCari").addEventListener("keypress", function(event) {
              if (event.key === "Enter") {
                event.preventDefault();
                cariData();
              }
            });
            
            muatData();
        </script>
    </body>
    </html>
    """

# ==========================================
# 4. ENDPOINTS API (BACKEND)
# ==========================================
@app.post("/hp/", response_model=HPResponse)
def tambah(hp: HPCreate, db: Session = Depends(get_db)):
    db_hp = HandphoneDB(**hp.dict())
    db.add(db_hp); db.commit(); db.refresh(db_hp); return db_hp

@app.get("/hp/", response_model=List[HPResponse])
def baca(q: Optional[str] = None, db: Session = Depends(get_db)): 
    if q:
        kata_kunci = f"%{q}%"
        return db.query(HandphoneDB).filter(
            or_(
                HandphoneDB.merk.ilike(kata_kunci),
                HandphoneDB.model.ilike(kata_kunci)
            )
        ).all()
    return db.query(HandphoneDB).all()

@app.put("/hp/{id}", response_model=HPResponse)
def update(id: int, hp: HPCreate, db: Session = Depends(get_db)):
    item = db.query(HandphoneDB).filter(HandphoneDB.id == id).first()
    for key, value in hp.dict().items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@app.delete("/hp/{id}")
def hapus(id: int, db: Session = Depends(get_db)):
    item = db.query(HandphoneDB).filter(HandphoneDB.id == id).first()
    db.delete(item); db.commit(); return {"pesan": "Dihapus"}