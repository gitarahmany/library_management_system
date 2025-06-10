from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask import session, flash
from flask_login import UserMixin
from flask_login import login_user
from flask_login import logout_user



app = Flask(__name__)

app.secret_key = 'your_secret_key'  # Replace with a secure value


# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirect to 'login' if not logged in


# Define the Book model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    is_available = db.Column(db.Boolean, default=True)  

class User(UserMixin, db.Model):  # ✅ Add UserMixin here
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Checkout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    checkout_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref='checkouts')
    book = db.relationship('Book', backref='checkouts')
    
# Create the database tables if they don't exist
with app.app_context():
    db.create_all()


@app.route('/')
def home_redirect():
    return redirect(url_for('view_books'))

# Route: Add Book (index)
@app.route('/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        new_book = Book(
            author=request.form['author'],
            language=request.form['language'],
            title=request.form['title']
        )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('view_books'))
    return render_template('add_book.html')

# Route: View Books
@app.route('/books')
@login_required
def view_books():
    books = Book.query.all()
    return render_template('books.html', books=books)

@app.route('/search', methods=['GET'])
@login_required
def search_books():
    query = request.args.get('query', '')

    results = []
    if query:
        results = Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.language.ilike(f'%{query}%'))
        ).all()

    return render_template('search.html', results=results)

# Route to edit a book
@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)

    if request.method == 'POST':
        book.author = request.form['author']
        book.language = request.form['language']
        book.title = request.form['title']
        db.session.commit()
        return redirect(url_for('view_books'))

    return render_template('edit_book.html', book=book)


# Route to delete a book
@app.route('/delete/<int:book_id>')
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    return redirect(url_for('view_books'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))

        new_user = User(name=name, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)  # ✅ Use Flask-Login to log in
            flash('Login successful!', 'success')
            return redirect(url_for('view_books'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()  # ✅ Cleanly logs out using Flask-Login
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/checkout/<int:book_id>')
def check_out_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_available = False
    db.session.commit()
    return redirect(url_for('view_books'))

@app.route('/checkin/<int:book_id>')
def check_in_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_available = True
    db.session.commit()
    return redirect(url_for('view_books'))



if __name__ == '__main__':
    app.run(debug=True)
