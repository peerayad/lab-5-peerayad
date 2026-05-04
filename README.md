# Lab 5 — GIX Equipment Tracker

**Student:** Peerayad  
**Live App:** https://510-lab5-peerayad.streamlit.app/  
**GitHub (Classroom):** https://github.com/GIX-Luyao/lab-5-peerayad

---

## How to access the app

Go to: **https://510-lab5-peerayad.streamlit.app/**

### Demo accounts

| Username | Password | Role |
|---|---|---|
| maason | maason123 | Approver (staff) |
| kevin | kevin123 | Approver (staff) |
| student1 | student123 | Requester (student) |
| student2 | student456 | Requester (student) |

---

## How to run locally

```bash
git clone https://github.com/GIX-Luyao/lab-5-peerayad.git
cd lab-5-peerayad
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:
```
SUPABASE_URL=https://fvfflrzixxastmdhfwqz.supabase.co
SUPABASE_KEY=your_anon_key_here
```

Run:
```bash
streamlit run app.py
```