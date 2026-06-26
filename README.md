# Placement Portal Application (PPA)

## Tech Stack
- **Backend**: Flask + SQLAlchemy
- **Frontend**: Vue 3 (CDN) + Bootstrap 5 (CDN)
- **Database**: SQLite (auto-created)

## Folder Structure
```
placement-portal/
├── app.py               ← Flask backend (all API routes)
├── requirements.txt
├── static/
│   ├── css/style.css    ← Custom styles
│   └── js/app.js        ← Vue 3 frontend logic
└── templates/
    └── index.html       ← Single HTML entry point (Jinja2 + Vue CDN)
```

## Setup (Windows 11 + VS Code)

### 1. Install Python packages
Open terminal in VS Code (`Ctrl + ~`) and run:
```
pip install -r requirements.txt
```

### 2. Run the server
```
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

## Default Admin Login
- **Email**: admin@placement.com
- **Password**: admin123

## User Roles & Flow

| Role    | What they do                                              |
|---------|-----------------------------------------------------------|
| Admin   | Pre-created. Approves companies, drives. Views all data.  |
| Company | Register → Admin approves → Create drives → Manage apps  |
| Student | Register → Login → View & apply for drives → Track status |

## Workflow
1. Start the app → Admin is auto-created in DB
2. Register a Company → Admin logs in and approves it
3. Company creates a Placement Drive → Admin approves it
4. Students register and login → Apply to approved drives
5. Company shortlists/selects students
6. Admin can view everything and blacklist users
