from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def anasayfa():
    current_date = datetime.now().strftime("%d %B %Y")
    return render_template('anasayfa.html', current_date=current_date)

@app.route('/takvim')
def takvim():
    return render_template('takvim.html')
    
if __name__ == '__main__':
    app.run(debug=True)