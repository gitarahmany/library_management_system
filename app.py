#importing the necessary libraries 
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

app.secret_key = 'your_secret_key'  # secures the management


# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initializes SQLAlchemy
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirect to 'login' if not logged in


# Define the Book model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True) #stores the id
    author = db.Column(db.String(100), nullable=False) #stores the author
    language = db.Column(db.String(50), nullable=False) #stores the language of the book
    title = db.Column(db.String(150), nullable=False) #stores the title of the book
    is_available = db.Column(db.Boolean, default=True)  #stores the availabity of the book

#define the user model - inherits from the db.model 
class User(UserMixin, db.Model): 
    id = db.Column(db.Integer, primary_key=True) #Stores the user ID, PK
    name = db.Column(db.String(100), nullable=False) #Stores the user name
    email = db.Column(db.String(120), unique=True, nullable=False) #Stores the user email
    password_hash = db.Column(db.String(128), nullable=False) #Stores the user password as "hash"

    def set_password(self, password): #set the hash password
        self.password_hash = generate_password_hash(password)

    def check_password(self, password): #verifies the hash password, check in the DB
        return check_password_hash(self.password_hash, password)

#Flask-Login uses this function to keep the user logged in between requests
@login_manager.user_loader
def load_user(user_id): #stored id
    return User.query.get(int(user_id)) #Look the user from the database by their ID and returns to the user object

#define the checkout model 
class Checkout(db.Model):
    id = db.Column(db.Integer, primary_key=True)  #PK: id for each checkout/ borrow
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) #FK: links the checkout to a user ID
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)#FK: links the checkout to a book ID
    checkout_date = db.Column(db.DateTime, default=datetime.utcnow) #stores the timing of checkout
    return_date = db.Column(db.DateTime, nullable=True) #store the return date

    #creates relationship for accessiablity 
    user = db.relationship('User', backref='checkouts') 
    book = db.relationship('Book', backref='checkouts')
    
# Create the database tables
with app.app_context():
    db.create_all()

#main page/ home route
@app.route('/')
def home_redirect(): #redirect to view books when in this root (/)
    return redirect(url_for('view_books')) #make url for the view books page

# Add book route
@app.route('/add', methods=['GET', 'POST']) #shows and process the form data
def add_book():
    if request.method == 'POST': #takes the data and store in DB
        new_book = Book(
            author=request.form['author'],
            language=request.form['language'],
            title=request.form['title']
        )
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('view_books'))
    return render_template('add_book.html') #display form if used "Get" method

# View Books route: shows all the books in the DB
@app.route('/books')
@login_required
def view_books():
    books = Book.query.all()
    return render_template('books.html', books=books)

#search books route
@app.route('/search', methods=['GET'])
@login_required
def search_books():
    query = request.args.get('query', '') #takes the query from the search

    results = []
    if query: #search all the DB for the book
        results = Book.query.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.language.ilike(f'%{query}%'))
        ).all()
    
    return render_template('search.html', results=results) #shows the search result

# Route to edit a book
@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id) #get the book based on ID and if not found, show the error

    if request.method == 'POST': #update the edited data
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

#user register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first() #checks for existing user to avoid duplicate
        if existing_user:
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))

        new_user = User(name=name, email=email) #add new user
        new_user.set_password(password) #store password
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

#the log in route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST': #ask and check the email and password
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)  
            flash('Login successful!', 'success')
            return redirect(url_for('view_books'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

#the logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()  #logs out the current user
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

#the book checkout route and shows unavilable
@app.route('/checkout/<int:book_id>')
def check_out_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_available = False
    db.session.commit()
    return redirect(url_for('view_books'))

#the book checkin route
@app.route('/checkin/<int:book_id>')
def check_in_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.is_available = True
    db.session.commit()
    return redirect(url_for('view_books'))


#runs app in debug for error and development
if __name__ == '__main__':
    app.run(debug=True)
