import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = '123456'

def openDbCon():
    DATABASE = 'book_catalogue.db'
    conn = sqlite3.connect(DATABASE)
    return conn


def init_db():
    con = openDbCon()
    cursor = con.cursor()
    with app.open_resource('schema.sql', mode='r') as schema_file:
        cursor.executescript(schema_file.read())
    con.commit()
    cursor.close()


# Extract required data from Book JSON Object
def extractBookData(book):
    author_list = list()
    isbn_13 = None
    pageCount = 0
    avg_rating = 0
    thumbnail_url = ''

    if 'volumeInfo' in book:
        info = book['volumeInfo']
        if 'authors' in info:
            for author in info['authors']:
                author_list.append(author)

        for isbn in info['industryIdentifiers']:
            if isbn['type'] == 'ISBN_13':
                isbn_13 = isbn['identifier']

        if 'pageCount' in info:
            pageCount = info['pageCount']

        if 'averageRating' in info:
            avg_rating = info['averageRating']

        if 'imageLinks' in info and 'thumbnail' in info['imageLinks']:
            thumbnail_url = info['imageLinks']['thumbnail']

    return {
        "isbn": isbn_13,
        "title": info['title'],
        "authors": ', '.join(author_list),
        "pageCount": pageCount,
        "rating": avg_rating,
        "thumbnail_url": thumbnail_url
    }


# Initialize database from schema.sql
init_db()


@app.route('/')
def index():
    current_user_id = 0
    error = None
    msg = None
    if 'user_id' in session:
        current_user_id = session['user_id']

    if 'error' in session:
        error = session['error']
        session.pop('error')

    if 'msg' in session:
        msg = session['msg']
        session.pop('msg')

    if current_user_id == 0:
        return render_template('login.html', error=error)
    else:
        cursor = openDbCon().cursor()
        cursor.execute('SELECT isbn, title, author, page_count, avg_rating, thumbnail_url FROM books WHERE (user_id=?)',
                       (current_user_id,))
        books = list()
        for book in cursor:
            print
            book
            books.append({
                "isbn": book[0],
                "title": book[1],
                "authors": book[2],
                "pageCount": book[3],
                "rating": book[4],
                "thumbnail_url": book[5]
            })

        cursor.close()
        return render_template('index.html', error=error, msg=msg, books=books, user=session['username'])


# Login Controller
@app.route('/login', methods=['POST', 'GET'])
def login():
    error = None
    username = ''
    password = ''

    if request.method == 'POST':
        if 'username' in request.form:
            username = request.form['username']

        if 'password' in request.form:
            password = request.form['password']

        if not username or not password:
            error = 'Username or Password is empty'

        # Fetch user from db
        cursor = openDbCon().cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE (username=? and password=?)',
                       (username, password,))

        user = check = cursor.fetchone()
        if user is None:
            error = 'Username / Password is invalid'
        else:
            session['user_id'] = user[0]
            session['username'] = user[1]

    if error:
        session['error'] = error
    else:
        session['msg'] = "Welcome user : " + username

    return redirect(url_for('index'))


# Logout Controller
@app.route('/logout', methods=['GET'])
def logout():
    for key in session.keys():
        session.pop(key)
    return redirect(url_for('index'))


# Search Controller
@app.route('/search')
def search():
    current_user_id = 0
    session['error'] = None

    if 'user_id' in session:
        current_user_id = session['user_id']

    search = None
    books = list()
    print(request.args)
    if current_user_id != 0:
        search = request.args.get('search')
        # print search # Debug

        if not search:
            session['error'] = 'Nothing to search!'
        else:
            # Call Google Books API

            # First search by ISBN. If no results, then search by Book Title
            r = requests.get('https://www.googleapis.com/books/v1/volumes?q=isbn:' + search)
            search_result = r.json()
            # print search_result['totalItems'] # Debug
            if 'totalItems' in search_result and search_result['totalItems'] != 0:
                for book in search_result['items']:
                    books.append(extractBookData(book))
            else:
                # Search book by Title
                # Ref: https://developers.google.com/books/docs/v1/using
                r = requests.get('https://www.googleapis.com/books/v1/volumes?q=intitle:' + search)
                search_result = r.json()
                if 'totalItems' in search_result and search_result['totalItems'] != 0:
                    for book in search_result['items']:
                        books.append(extractBookData(book))
                else:
                    session['error'] = "No books found."
        if not session['error']:
            return render_template('search.html', books=books, search_key=search)
        else:
            return redirect(url_for('index'))
    else:
        session['error'] = 'Nothing to search!'
        return redirect(url_for('index'))


# Store book Controller
@app.route('/storebook', methods=['POST', 'GET'])
def storebook():
    current_user_id = 0
    error = None
    if 'user_id' in session:
        current_user_id = session['user_id']
    isbn = None
    title = None
    authors = None
    pageCount = None
    rating = None
    thumbnail_url = None

    if current_user_id != 0 and request.method == 'POST':
        if 'isbn' in request.form:
            isbn = request.form['isbn']

        if 'title' in request.form:
            title = request.form['title']

        if 'authors' in request.form:
            authors = request.form['authors']

        if 'pageCount' in request.form:
            pageCount = request.form['pageCount']

        if 'rating' in request.form:
            rating = request.form['rating']

        if 'thumbnail_url' in request.form:
            thumbnail_url = request.form['thumbnail_url']

        if not isbn or not title or not authors or not pageCount or not rating or not thumbnail_url:
            error = 'Error! Unable to add book.'
        else:
            # Insert book in DB
            con = openDbCon()
            cursor = con.cursor()

            # Check if book already exists in catalogue
            cursor.execute('SELECT * FROM books WHERE (user_id=? AND isbn=?)', (current_user_id, isbn))
            check = cursor.fetchone()
            if check is None:
                cursor.execute(
                    "INSERT INTO books(user_id, isbn, title, author, page_count, avg_rating, thumbnail_url) values (?, ?, ?, ?, ?, ?, ?)",
                    (current_user_id, isbn, title, authors,
                     pageCount, rating, thumbnail_url))
            else:
                error = "Book already present in catalogue."

            con.commit()
            cursor.close()
    if error:
        session['error'] = error
    else:
        session['msg'] = "Book added sucessfully"

    return redirect(url_for('index'))


# Delete book Controller
@app.route('/deletebook', methods=['POST', 'GET'])
def deletebook():
    current_user_id = 0
    error = None

    if 'user_id' in session:
        current_user_id = session['user_id']

    isbn = None

    if current_user_id != 0 and request.method == 'POST':
        if 'isbn' in request.form:
            isbn = request.form['isbn']

        if not isbn:
            error = 'Error! Unable to add book.'
        else:
            # Delete book in DB
            con = openDbCon()
            cursor = con.cursor()

            # Check if book already exists in catalogue
            cursor.execute('SELECT * FROM books WHERE (user_id=? AND isbn=?)', (current_user_id, isbn))
            check = cursor.fetchone()
            if check is None:
                error = "Unable to find book in catelogue."
            else:
                cursor.execute(
                    "DELETE FROM books WHERE (user_id=? AND isbn=?)",
                    (current_user_id, isbn,))

            con.commit()
            cursor.close()

    if error:
        session['error'] = error
    else:
        session['msg'] = "Book delete sucessfully"

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=False)