# Green View Borrowing Club

A responsive web application built around the hostel borrowing OOP system in [`backend/inclass.py`](./backend/inclass.py).

## Run

From the repository root, using Node.js/npm:

```powershell
npm install
npm run build
```

`npm install` creates `.venv` if needed and installs the Python backend dependencies. `npm run build` starts the Flask app on http://127.0.0.1:5000; keep that terminal open and open the URL in your browser. The app binds to localhost only.

To run in development mode instead, use `npm run dev`.

## Project structure

```text
backend/           Flask API and OOP domain model
frontend/static/   CSS and JavaScript
index.html         Application page
run.py             Application launcher
requirements.txt   Python dependencies
package.json       Local setup and run commands
```

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin123` |
| Member | `brian` | `pass1` |
| Member | `grace` | `pass2` |
| Member | `simon` | `pass3` |

Demo data resets whenever the server restarts.
